/**
 * Format lap time in seconds to mm:ss.SSS or +X.Xs for gaps.
 * @param {number} seconds
 * @returns {string}
 */
export function formatLapTime(seconds) {
	if (seconds == null) return '-';
	const mins = Math.floor(seconds / 60);
	const secs = seconds % 60;
	if (mins > 0) {
		return `${mins}:${secs.toFixed(3).padStart(6, '0')}`;
	}
	return secs.toFixed(3);
}

/**
 * Format gap value as "+X.Xs" or "Leader".
 * @param {number|null} gap
 * @returns {string}
 */
export function formatGap(gap) {
	if (gap == null) return '-';
	if (gap === 0) return 'Leader';
	return `+${gap.toFixed(1)}s`;
}

/**
 * Format delta as "+X.XX" or "-X.XX".
 * @param {number|null} delta
 * @returns {string}
 */
export function formatDelta(delta) {
	if (delta == null) return '-';
	const sign = delta >= 0 ? '+' : '';
	return `${sign}${delta.toFixed(2)}`;
}

/**
 * Format percentage to 1 decimal.
 * @param {number} pct
 * @returns {string}
 */
export function formatPct(pct) {
	if (pct == null) return '-';
	return `${pct.toFixed(1)}%`;
}

/**
 * Compute gap-to-leader for each driver per lap.
 * Excludes laps where time_s is null or is_accurate is false.
 * @param {Array<{driver: string, team: string, laps: Array}>} allDriverLaps
 * @returns {Array<{driver: string, team: string, laps: Array}>}
 */
export function computeGapToLeader(allDriverLaps) {
	const fastestPerLap = {};

	for (const { laps } of allDriverLaps) {
		for (const lap of laps) {
			if (lap.time_s == null || lap.is_accurate === false) continue;
			if (!fastestPerLap[lap.lap] || lap.time_s < fastestPerLap[lap.lap]) {
				fastestPerLap[lap.lap] = lap.time_s;
			}
		}
	}

	return allDriverLaps.map((driver) => ({
		...driver,
		laps: driver.laps.map((lap) => ({
			...lap,
			gap:
				lap.time_s != null && lap.is_accurate !== false && fastestPerLap[lap.lap]
					? +(lap.time_s - fastestPerLap[lap.lap]).toFixed(2)
					: null,
		})),
	}));
}
