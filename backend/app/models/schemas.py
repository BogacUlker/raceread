from pydantic import BaseModel


class RaceInfo(BaseModel):
    id: str
    name: str
    date: str
    circuit: str
    winner: str
    total_laps: int


class LapData(BaseModel):
    lap: int
    time_s: float | None
    s1: float | None
    s2: float | None
    s3: float | None
    compound: str | None
    tire_age: int | None
    position: int | None
    track_status: str | None
    is_personal_best: bool | None
    speed_i1: float | None
    speed_i2: float | None
    speed_fl: float | None
    speed_st: float | None
    is_accurate: bool | None


class DriverLaps(BaseModel):
    driver: str
    team: str
    laps: list[LapData]


class EnergyLap(BaseModel):
    lap: int
    deploy_pct: float
    harvest_pct: float
    clip_pct: float
    neutral_pct: float
    normalized_deploy: float
    normalized_harvest: float
    normalized_clip: float
    is_vsc: bool


class DriverEnergy(BaseModel):
    driver: str
    team: str
    laps: list[EnergyLap]


class EnergyComparisonEntry(BaseModel):
    driver: str
    team: str
    deploy_pct: float
    harvest_pct: float
    clip_pct: float
    dc_ratio: float
    rank: int


class EnergyComparisonResponse(BaseModel):
    race_id: str
    entries: list[EnergyComparisonEntry]


class VSCEnergyProfile(BaseModel):
    deploy: float
    harvest: float
    clip: float


class VSCComparisonEntry(BaseModel):
    driver: str
    team: str
    vsc: VSCEnergyProfile
    normal: VSCEnergyProfile


class VSCComparisonResponse(BaseModel):
    race_id: str
    vsc_laps: list[int]
    sc_laps: list[int] = []
    entries: list[VSCComparisonEntry]


class Stint(BaseModel):
    compound: str
    start_lap: int
    end_lap: int
    laps: int


class DriverStrategy(BaseModel):
    driver: str
    team: str
    stints: list[Stint]
    pit_laps: list[int]


class StrategyResponse(BaseModel):
    race_id: str
    drivers: list[DriverStrategy]


class DeltaMatrixResponse(BaseModel):
    race_id: str
    drivers: list[str]
    matrix: list[list[float | None]]


class Annotation(BaseModel):
    driver: str | None = None
    lap: int | None = None
    chart_type: str
    text_tr: str
    text_en: str
    category: str
    severity: str


class AnnotationsResponse(BaseModel):
    race_id: str
    annotations: list[Annotation]


class QualifyingSessionResult(BaseModel):
    s1: float | None = None
    s2: float | None = None
    s3: float | None = None


class QualifyingAttempt(BaseModel):
    attempt_number: int
    session: str  # "Q1", "Q2", "Q3"
    time_s: float | None = None
    time_str: str | None = None
    s1: float | None = None
    s2: float | None = None
    s3: float | None = None
    compound: str | None = None
    is_deleted: bool = False
    is_personal_best: bool = False


class QualifyingDriver(BaseModel):
    driver: str
    team: str
    position: int | None = None
    grid_position: int | None = None
    q1: str | None = None
    q1_s: float | None = None
    q2: str | None = None
    q2_s: float | None = None
    q3: str | None = None
    q3_s: float | None = None
    eliminated_in: str | None = None
    sectors: QualifyingSessionResult = QualifyingSessionResult()
    sectors_q1: QualifyingSessionResult = QualifyingSessionResult()
    sectors_q2: QualifyingSessionResult = QualifyingSessionResult()
    sectors_q3: QualifyingSessionResult = QualifyingSessionResult()
    gap_to_pole: float | None = None
    attempts: list[QualifyingAttempt] = []


class QualifyingResponse(BaseModel):
    race_id: str
    drivers: list[QualifyingDriver]


class QualifyingTelemetrySample(BaseModel):
    time_s: float
    dist: float
    speed: float
    x: float
    y: float
    throttle: float | None = None
    brake: bool = False
    gear: int | None = None


class QualifyingTelemetryDriver(BaseModel):
    driver: str
    team: str
    session: str  # "Q1", "Q2", "Q3"
    lap_time_s: float
    samples: list[QualifyingTelemetrySample]


class QualifyingTelemetryResponse(BaseModel):
    race_id: str
    drivers: list[QualifyingTelemetryDriver]


# ---------------------------------------------------------------------------
# Pit stop analysis schemas
# ---------------------------------------------------------------------------


class PitStopDetail(BaseModel):
    lap: int
    time_loss_s: float | None = None
    compound_from: str | None = None
    compound_to: str | None = None
    under_sc: bool = False


class DriverPitStats(BaseModel):
    driver: str
    team: str
    pits: list[PitStopDetail]
    total_time_lost_s: float
    num_stops: int


class PitStatsResponse(BaseModel):
    race_id: str
    drivers: list[DriverPitStats]


# ---------------------------------------------------------------------------
# Telemetry schemas (MVP-2)
# ---------------------------------------------------------------------------


class TelemetrySample(BaseModel):
    dist: float | None = None
    speed: float | None = None
    throttle: float | None = None
    brake: bool = False
    gear: int | None = None
    rpm: int | None = None
    x: float | None = None
    y: float | None = None
    driver_ahead: str | None = None
    gap_ahead: float | None = None
    energy: str = "N"


class LapTelemetry(BaseModel):
    lap: int
    samples: list[TelemetrySample]


class DriverTelemetry(BaseModel):
    driver: str
    team: str
    laps: list[LapTelemetry]


class CircuitCorner(BaseModel):
    number: int
    x: float
    y: float
    angle: float
    distance: float
    letter: str = ""


class CircuitInfo(BaseModel):
    corners: list[CircuitCorner]
    outline: list[dict]
    track_length: int
