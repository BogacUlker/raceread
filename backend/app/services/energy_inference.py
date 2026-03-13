"""
Energy inference engine for RaceRead.

Infers battery energy states (DEPLOYING, HARVESTING, CLIPPING, NEUTRAL)
from publicly available F1 telemetry data. Actual battery/ERS data is not
broadcast - this module reconstructs energy behavior using acceleration
residual analysis against an ICE-only baseline.

Algorithm:
    1. Convert speed to m/s, compute acceleration via finite differences
    2. Smooth acceleration with Gaussian filter to reduce sensor noise
    3. Build ICE baseline: median + std of acceleration per speed bin
       for samples at full throttle with no braking
    4. Classify each telemetry sample by comparing observed acceleration
       against the baseline envelope
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d

from backend.app.config import (
    CLIP_SIGMA,
    CLIP_THROTTLE_MIN,
    DEPLOY_SIGMA,
    DEPLOY_THROTTLE_MIN,
    GAUSSIAN_SIGMA,
    HARVEST_DECEL,
    SPEED_BIN_WIDTH,
)

logger = logging.getLogger(__name__)


class EnergyState(str, Enum):
    """Possible inferred energy states for a telemetry sample."""

    DEPLOYING = "DEPLOYING"
    HARVESTING = "HARVESTING"
    CLIPPING = "CLIPPING"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class EnergyThresholds:
    """Configurable thresholds for the energy state classifier.

    Attributes:
        deploy_sigma: Number of standard deviations above baseline median
            that indicates electrical energy deployment. Default 1.5.
        clip_sigma: Number of standard deviations below baseline median
            that indicates super-clipping (ICE power stolen for charging).
            Default 2.0.
        harvest_decel: Deceleration threshold (m/s^2, negative) below which
            braking/coasting samples are classified as harvesting. Default -0.3.
        deploy_throttle_min: Minimum throttle percentage for a sample to be
            eligible for DEPLOYING classification. Default 80.
        clip_throttle_min: Minimum throttle percentage for a sample to be
            eligible for CLIPPING classification. Default 95.
        gaussian_sigma: Sigma for Gaussian smoothing of the acceleration
            signal. Default 1.5.
        speed_bin_width: Width of speed bins in km/h for the ICE baseline.
            Default 10.
        min_bin_samples: Minimum number of samples in a speed bin for the
            bin to be included in the baseline. Default 5.
        min_lap_samples: Minimum number of telemetry samples for a lap to
            be processed. Laps below this threshold are skipped. Default 10.
    """

    deploy_sigma: float = DEPLOY_SIGMA
    clip_sigma: float = CLIP_SIGMA
    harvest_decel: float = HARVEST_DECEL
    deploy_throttle_min: float = DEPLOY_THROTTLE_MIN
    clip_throttle_min: float = CLIP_THROTTLE_MIN
    gaussian_sigma: float = GAUSSIAN_SIGMA
    speed_bin_width: float = SPEED_BIN_WIDTH
    min_bin_samples: int = 5
    min_lap_samples: int = 10


@dataclass(frozen=True)
class SpeedBinBaseline:
    """ICE-only acceleration baseline for a single speed bin.

    Attributes:
        speed_min: Lower bound of the speed bin in km/h.
        speed_max: Upper bound of the speed bin in km/h.
        median: Median acceleration (m/s^2) when only ICE is powering the car.
        std: Standard deviation of acceleration in this bin.
        sample_count: Number of samples used to compute the baseline.
    """

    speed_min: float
    speed_max: float
    median: float
    std: float
    sample_count: int


def _compute_acceleration(
    speed_kmh: np.ndarray,
    time_seconds: np.ndarray,
    sigma: float,
) -> np.ndarray:
    """Compute smoothed longitudinal acceleration from speed telemetry.

    Args:
        speed_kmh: Speed values in km/h.
        time_seconds: Corresponding timestamps in seconds (monotonic).
        sigma: Gaussian smoothing sigma applied after differentiation.

    Returns:
        Array of acceleration values in m/s^2, same length as input.
        First element is set to 0.0 (no backward difference available).
    """
    speed_ms = speed_kmh / 3.6

    dt = np.diff(time_seconds)
    dv = np.diff(speed_ms)

    # Avoid division by zero for duplicate timestamps
    dt_safe = np.where(dt > 0, dt, np.nan)
    raw_accel = dv / dt_safe

    # Replace NaN from zero-dt with 0.0
    raw_accel = np.nan_to_num(raw_accel, nan=0.0)

    # Prepend 0.0 for the first sample (no backward diff)
    raw_accel = np.concatenate([[0.0], raw_accel])

    # Smooth to reduce sensor noise
    if len(raw_accel) > 3 and sigma > 0:
        smoothed = gaussian_filter1d(raw_accel, sigma=sigma)
    else:
        smoothed = raw_accel

    return smoothed


def _timedelta_to_seconds(time_series: pd.Series) -> np.ndarray:
    """Convert a pandas Series of timedelta or datetime to float seconds.

    Handles both timedelta64 and datetime64 types. For timedelta, converts
    directly. For datetime, computes offset from the first value.

    Args:
        time_series: Pandas Series containing time information.

    Returns:
        Numpy array of float64 seconds.
    """
    if pd.api.types.is_timedelta64_dtype(time_series):
        return time_series.dt.total_seconds().to_numpy(dtype=np.float64)

    if pd.api.types.is_datetime64_any_dtype(time_series):
        offset = time_series.iloc[0]
        return (time_series - offset).dt.total_seconds().to_numpy(dtype=np.float64)

    # Try numeric interpretation as a fallback
    return time_series.to_numpy(dtype=np.float64)


def build_ice_baseline(
    telemetry_df: pd.DataFrame,
    thresholds: EnergyThresholds | None = None,
) -> dict[int, SpeedBinBaseline]:
    """Build the ICE-only acceleration baseline from telemetry data.

    Selects samples where the driver is at near-full throttle with no braking
    (Throttle >= clip_throttle_min and Brake == False). These samples represent
    pure ICE power without significant electrical contribution. Groups by speed
    bins and computes median + std of acceleration for each bin.

    Args:
        telemetry_df: DataFrame with columns Speed, Throttle, Brake, and a
            pre-computed 'acceleration' column.
        thresholds: Classification thresholds. Defaults to EnergyThresholds().

    Returns:
        Dictionary mapping speed bin index (bin_lower / bin_width) to the
        SpeedBinBaseline for that bin. Bins with fewer than min_bin_samples
        are excluded.
    """
    if thresholds is None:
        thresholds = EnergyThresholds()

    # Select ICE-only samples: high throttle, no braking
    mask = (telemetry_df["Throttle"] >= thresholds.clip_throttle_min) & (
        ~telemetry_df["Brake"].astype(bool)
    )
    ice_samples = telemetry_df.loc[mask].copy()

    if ice_samples.empty:
        logger.warning("No ICE-only samples found for baseline construction")
        return {}

    # Assign speed bins
    bin_width = thresholds.speed_bin_width
    ice_samples["speed_bin"] = (ice_samples["Speed"] // bin_width).astype(int)

    baseline: dict[int, SpeedBinBaseline] = {}

    for bin_idx, group in ice_samples.groupby("speed_bin"):
        if len(group) < thresholds.min_bin_samples:
            continue

        accel_values = group["acceleration"].to_numpy()
        median_accel = float(np.median(accel_values))
        std_accel = float(np.std(accel_values, ddof=1)) if len(group) > 1 else 0.0

        # Ensure std is never zero to avoid trivial thresholds
        if std_accel < 1e-6:
            std_accel = 0.1

        baseline[int(bin_idx)] = SpeedBinBaseline(
            speed_min=float(bin_idx * bin_width),
            speed_max=float((bin_idx + 1) * bin_width),
            median=median_accel,
            std=std_accel,
            sample_count=len(group),
        )

    logger.info(
        "Built ICE baseline with %d speed bins from %d samples",
        len(baseline),
        len(ice_samples),
    )
    return baseline


def classify_samples(
    telemetry_df: pd.DataFrame,
    baseline: dict[int, SpeedBinBaseline],
    thresholds: EnergyThresholds | None = None,
) -> np.ndarray:
    """Classify each telemetry sample into an energy state.

    Classification rules applied in priority order:
        1. DEPLOYING: Throttle >= deploy_throttle_min AND acceleration exceeds
           baseline_median + deploy_sigma * std for the sample's speed bin.
        2. CLIPPING: Throttle >= clip_throttle_min AND acceleration is below
           baseline_median - clip_sigma * std for the sample's speed bin.
        3. HARVESTING: (Brake == True OR Throttle < 20) AND acceleration
           is below harvest_decel threshold.
        4. NEUTRAL: All remaining samples.

    Args:
        telemetry_df: DataFrame with columns Speed, Throttle, Brake,
            and pre-computed 'acceleration'.
        baseline: ICE baseline from build_ice_baseline().
        thresholds: Classification thresholds. Defaults to EnergyThresholds().

    Returns:
        Numpy array of EnergyState values, one per telemetry row.
    """
    if thresholds is None:
        thresholds = EnergyThresholds()

    n = len(telemetry_df)

    # Use string values internally to avoid numpy dtype=object corruption
    # of enum values (np.full truncates str-enum to first 7 chars).
    _NEUTRAL = EnergyState.NEUTRAL.value
    _DEPLOYING = EnergyState.DEPLOYING.value
    _HARVESTING = EnergyState.HARVESTING.value
    _CLIPPING = EnergyState.CLIPPING.value

    states: list[str] = [_NEUTRAL] * n

    speed = telemetry_df["Speed"].to_numpy(dtype=np.float64)
    throttle = telemetry_df["Throttle"].to_numpy(dtype=np.float64)
    brake = telemetry_df["Brake"].to_numpy(dtype=bool)
    accel = telemetry_df["acceleration"].to_numpy(dtype=np.float64)

    bin_width = thresholds.speed_bin_width

    # Pre-compute speed bin indices for all samples
    speed_bins = (speed // bin_width).astype(int)

    for i in range(n):
        bin_idx = speed_bins[i]

        # Check harvesting first - this doesn't need baseline
        if (brake[i] or throttle[i] < 20.0) and accel[i] < thresholds.harvest_decel:
            states[i] = _HARVESTING
            continue

        # Baseline-dependent classifications require a valid bin
        if bin_idx not in baseline:
            # No baseline data for this speed range, remain NEUTRAL
            continue

        bin_data = baseline[bin_idx]
        deploy_threshold = bin_data.median + thresholds.deploy_sigma * bin_data.std
        clip_threshold = bin_data.median - thresholds.clip_sigma * bin_data.std

        # DEPLOYING: high throttle + acceleration above baseline envelope
        if throttle[i] >= thresholds.deploy_throttle_min and accel[i] > deploy_threshold:
            states[i] = _DEPLOYING
        # CLIPPING: very high throttle + acceleration below baseline envelope
        elif throttle[i] >= thresholds.clip_throttle_min and accel[i] < clip_threshold:
            states[i] = _CLIPPING

    return np.array(states, dtype=object)


def normalize_active_states(
    deploy_pct: float,
    harvest_pct: float,
    clip_pct: float,
) -> tuple[float, float, float]:
    """Normalize energy state percentages excluding neutral.

    Neutral typically accounts for ~73% of samples and drowns the signal
    from active energy states. This function rescales deploy, harvest, and
    clip percentages so they sum to 100%.

    Args:
        deploy_pct: Raw deploy percentage (0-100).
        harvest_pct: Raw harvest percentage (0-100).
        clip_pct: Raw clip percentage (0-100).

    Returns:
        Tuple of (normalized_deploy, normalized_harvest, normalized_clip),
        each rounded to 2 decimal places and summing to ~100%.
        Returns (0.0, 0.0, 0.0) if all active states are zero.
    """
    total = deploy_pct + harvest_pct + clip_pct

    if total < 1e-9:
        return 0.0, 0.0, 0.0

    norm_deploy = round((deploy_pct / total) * 100.0, 2)
    norm_harvest = round((harvest_pct / total) * 100.0, 2)
    norm_clip = round((clip_pct / total) * 100.0, 2)

    return norm_deploy, norm_harvest, norm_clip


def compute_dc_ratio(normalized_deploy: float, normalized_clip: float) -> float:
    """Compute the Deploy/Clip ratio.

    Higher ratio indicates more efficient energy usage - the driver deploys
    more electrical energy relative to how often they are clipped.

    RUS 2.95 (most efficient in 2026 Australia), HAM 1.26 (least efficient).

    Args:
        normalized_deploy: Normalized deploy percentage (0-100).
        normalized_clip: Normalized clip percentage (0-100).

    Returns:
        Deploy/Clip ratio, rounded to 2 decimal places.
        Returns 0.0 if clip is zero (avoids division by zero).
    """
    if normalized_clip < 1e-9:
        return 0.0

    return round(normalized_deploy / normalized_clip, 2)


def _compute_lap_energy(
    lap_df: pd.DataFrame,
    baseline: dict[int, SpeedBinBaseline],
    thresholds: EnergyThresholds,
) -> dict[str, float] | None:
    """Compute energy state percentages for a single lap.

    Args:
        lap_df: Telemetry DataFrame for one lap, must contain 'acceleration'.
        baseline: ICE baseline dictionary.
        thresholds: Classification thresholds.

    Returns:
        Dictionary with raw and normalized percentages, or None if the lap
        has too few samples.
    """
    n = len(lap_df)
    if n < thresholds.min_lap_samples:
        return None

    states = classify_samples(lap_df, baseline, thresholds)

    deploy_count = np.sum(states == EnergyState.DEPLOYING.value)
    harvest_count = np.sum(states == EnergyState.HARVESTING.value)
    clip_count = np.sum(states == EnergyState.CLIPPING.value)
    neutral_count = np.sum(states == EnergyState.NEUTRAL.value)

    deploy_pct = round(float(deploy_count / n) * 100.0, 2)
    harvest_pct = round(float(harvest_count / n) * 100.0, 2)
    clip_pct = round(float(clip_count / n) * 100.0, 2)
    neutral_pct = round(float(neutral_count / n) * 100.0, 2)

    norm_deploy, norm_harvest, norm_clip = normalize_active_states(
        deploy_pct, harvest_pct, clip_pct
    )

    return {
        "deploy_pct": deploy_pct,
        "harvest_pct": harvest_pct,
        "clip_pct": clip_pct,
        "neutral_pct": neutral_pct,
        "normalized_deploy": norm_deploy,
        "normalized_harvest": norm_harvest,
        "normalized_clip": norm_clip,
    }


def _prepare_telemetry(
    telemetry_df: pd.DataFrame,
    thresholds: EnergyThresholds,
) -> pd.DataFrame:
    """Prepare telemetry DataFrame by computing acceleration.

    Validates required columns exist, computes time in seconds, and derives
    the smoothed acceleration signal.

    Args:
        telemetry_df: Raw telemetry DataFrame from FastF1.
        thresholds: Thresholds containing gaussian_sigma.

    Returns:
        Copy of the DataFrame with 'time_seconds' and 'acceleration' columns
        added.

    Raises:
        ValueError: If required columns are missing.
    """
    required_cols = {"Speed", "Throttle", "Brake"}
    missing = required_cols - set(telemetry_df.columns)
    if missing:
        raise ValueError(f"Telemetry DataFrame missing required columns: {missing}")

    # Determine time column
    time_col = None
    for candidate in ("Time", "SessionTime", "Date"):
        if candidate in telemetry_df.columns:
            time_col = candidate
            break

    if time_col is None:
        raise ValueError(
            "Telemetry DataFrame must contain a time column "
            "(one of: Time, SessionTime, Date)"
        )

    df = telemetry_df.copy()

    # Convert time to seconds
    df["time_seconds"] = _timedelta_to_seconds(df[time_col])

    # Compute smoothed acceleration
    df["acceleration"] = _compute_acceleration(
        speed_kmh=df["Speed"].to_numpy(dtype=np.float64),
        time_seconds=df["time_seconds"].to_numpy(dtype=np.float64),
        sigma=thresholds.gaussian_sigma,
    )

    return df


def infer_energy_states(
    telemetry_df: pd.DataFrame,
    driver: str,
    team: str,
    vsc_laps: list[int] | None = None,
    thresholds: EnergyThresholds | None = None,
) -> dict[str, Any]:
    """Infer battery energy states from telemetry data for a single driver.

    This is the main entry point for the energy inference engine. It processes
    raw telemetry, builds an ICE baseline, classifies every sample, and
    aggregates results per lap.

    Args:
        telemetry_df: Telemetry DataFrame from FastF1 with columns:
            Speed (km/h), Throttle (0-100), Brake (bool),
            Time or SessionTime (timedelta/datetime),
            LapNumber (int).
        driver: Driver abbreviation (e.g., "RUS").
        team: Team name (e.g., "Mercedes").
        vsc_laps: List of lap numbers that occurred under Virtual Safety Car.
            Used to tag laps in output. Defaults to empty list.
        thresholds: Energy classification thresholds.
            Defaults to EnergyThresholds() which reads from config.

    Returns:
        Dictionary with driver info, per-lap energy data, and summary
        statistics. Structure matches the API response schema:

        {
            "driver": "RUS",
            "team": "Mercedes",
            "laps": [
                {
                    "lap": 1,
                    "deploy_pct": 3.00,
                    "harvest_pct": 22.80,
                    "clip_pct": 1.01,
                    "neutral_pct": 73.19,
                    "normalized_deploy": 11.2,
                    "normalized_harvest": 85.0,
                    "normalized_clip": 3.8,
                    "is_vsc": false
                },
                ...
            ],
            "summary": {
                "avg_deploy": 3.00,
                "avg_harvest": 22.80,
                "avg_clip": 1.01,
                "avg_neutral": 73.19,
                "normalized_deploy": 11.2,
                "normalized_harvest": 85.0,
                "normalized_clip": 3.8,
                "dc_ratio": 2.95
            }
        }

    Raises:
        ValueError: If required telemetry columns are missing.
    """
    if thresholds is None:
        thresholds = EnergyThresholds()

    if vsc_laps is None:
        vsc_laps = []

    vsc_set = set(vsc_laps)

    if telemetry_df.empty:
        logger.warning("Empty telemetry DataFrame for driver %s", driver)
        return {
            "driver": driver,
            "team": team,
            "laps": [],
            "summary": _empty_summary(),
        }

    # Validate LapNumber column exists
    if "LapNumber" not in telemetry_df.columns:
        raise ValueError(
            "Telemetry DataFrame must contain 'LapNumber' column. "
            "Use FastF1 lap.get_telemetry() which includes this field."
        )

    # Prepare telemetry: add acceleration column
    df = _prepare_telemetry(telemetry_df, thresholds)

    # Build ICE baseline from all laps combined for better statistics
    baseline = build_ice_baseline(df, thresholds)

    if not baseline:
        logger.warning(
            "Could not build ICE baseline for driver %s - "
            "insufficient full-throttle samples",
            driver,
        )
        return {
            "driver": driver,
            "team": team,
            "laps": [],
            "summary": _empty_summary(),
        }

    logger.info(
        "Processing energy states for %s (%s): %d total samples, %d baseline bins",
        driver,
        team,
        len(df),
        len(baseline),
    )

    # Process each lap
    lap_results: list[dict[str, Any]] = []
    lap_groups = df.groupby("LapNumber", sort=True)

    for lap_number, lap_df in lap_groups:
        energy = _compute_lap_energy(lap_df, baseline, thresholds)

        if energy is None:
            logger.debug(
                "Skipping lap %d for %s: insufficient samples (%d < %d)",
                lap_number,
                driver,
                len(lap_df),
                thresholds.min_lap_samples,
            )
            continue

        lap_results.append(
            {
                "lap": int(lap_number),
                "deploy_pct": energy["deploy_pct"],
                "harvest_pct": energy["harvest_pct"],
                "clip_pct": energy["clip_pct"],
                "neutral_pct": energy["neutral_pct"],
                "normalized_deploy": energy["normalized_deploy"],
                "normalized_harvest": energy["normalized_harvest"],
                "normalized_clip": energy["normalized_clip"],
                "is_vsc": int(lap_number) in vsc_set,
            }
        )

    # Compute summary statistics across all valid laps
    summary = _compute_summary(lap_results)

    logger.info(
        "Energy inference complete for %s: %d laps processed, DC ratio=%.2f",
        driver,
        len(lap_results),
        summary.get("dc_ratio", 0.0),
    )

    return {
        "driver": driver,
        "team": team,
        "laps": lap_results,
        "summary": summary,
    }


def _compute_summary(lap_results: list[dict[str, Any]]) -> dict[str, float]:
    """Compute summary statistics across all processed laps.

    Args:
        lap_results: List of per-lap energy dictionaries.

    Returns:
        Summary dictionary with averages and DC ratio.
    """
    if not lap_results:
        return _empty_summary()

    n = len(lap_results)

    avg_deploy = round(sum(lap["deploy_pct"] for lap in lap_results) / n, 2)
    avg_harvest = round(sum(lap["harvest_pct"] for lap in lap_results) / n, 2)
    avg_clip = round(sum(lap["clip_pct"] for lap in lap_results) / n, 2)
    avg_neutral = round(sum(lap["neutral_pct"] for lap in lap_results) / n, 2)

    norm_deploy, norm_harvest, norm_clip = normalize_active_states(
        avg_deploy, avg_harvest, avg_clip
    )

    dc_ratio = compute_dc_ratio(norm_deploy, norm_clip)

    return {
        "avg_deploy": avg_deploy,
        "avg_harvest": avg_harvest,
        "avg_clip": avg_clip,
        "avg_neutral": avg_neutral,
        "normalized_deploy": norm_deploy,
        "normalized_harvest": norm_harvest,
        "normalized_clip": norm_clip,
        "dc_ratio": dc_ratio,
    }


def _empty_summary() -> dict[str, float]:
    """Return a zeroed-out summary for edge cases."""
    return {
        "avg_deploy": 0.0,
        "avg_harvest": 0.0,
        "avg_clip": 0.0,
        "avg_neutral": 0.0,
        "normalized_deploy": 0.0,
        "normalized_harvest": 0.0,
        "normalized_clip": 0.0,
        "dc_ratio": 0.0,
    }
