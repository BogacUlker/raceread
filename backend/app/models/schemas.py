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
