/** Team colors - FastF1 base hues, lightened just enough to pass WCAG AA (4.5:1) as text on card backgrounds */
export const TEAM_COLORS = {
	'Mercedes': '#00D7B6',
	'Red Bull Racing': '#5087D9',
	'Ferrari': '#F73B54',
	'McLaren': '#F47600',
	'Aston Martin': '#229971',
	'Alpine': '#00A1E8',
	'Williams': '#4A8AE8',
	'Racing Bulls': '#6C98FF',
	'Audi': '#FF4066',
	'Haas F1 Team': '#9C9FA2',
	'Cadillac': '#909090',
	/* 2021-era teams (Classics) */
	'AlphaTauri': '#5D8AB5',
	'Alfa Romeo Racing': '#E85454',
	'Alfa Romeo': '#E85454',
};

/** Energy state colors */
export const ENERGY_COLORS = {
	deploy: '#22C55E',
	harvest: '#3B82F6',
	clip: '#F59E0B',
	neutral: '#6B7280',
};

/** Tyre compound colors (standard F1) */
export const COMPOUND_COLORS = {
	SOFT: '#FF3333',
	MEDIUM: '#FFC300',
	HARD: '#F0F0F0',
	INTERMEDIATE: '#39B54A',
	WET: '#0067FF',
};

/** Annotation category colors */
export const ANNOTATION_COLORS = {
	pace_anomaly: '#E24B4A',
	energy_shift: '#F59E0B',
	safety_car: '#3B82F6',
	pit_stop: '#6B7280',
	position_change: '#22C55E',
	fastest_lap: '#A855F7',
	race_insight: '#8B5CF6',
	energy_insight: '#F59E0B',
	traffic_insight: '#06B6D4',
	qualifying_insight: '#A855F7',
};

/** Turkish Grand Prix name translations (keyed by English full name) */
export const RACE_NAMES_TR = {
	'Australian Grand Prix': 'Avustralya Grand Prix',
	'Chinese Grand Prix': 'Çin Grand Prix',
	'Japanese Grand Prix': 'Japonya Grand Prix',
	'Bahrain Grand Prix': 'Bahreyn Grand Prix',
	'Saudi Arabian Grand Prix': 'Suudi Arabistan Grand Prix',
	'Miami Grand Prix': 'Miami Grand Prix',
	'Canadian Grand Prix': 'Kanada Grand Prix',
	'Monaco Grand Prix': 'Monako Grand Prix',
	'Barcelona Grand Prix': 'Barselona Grand Prix',
	'Austrian Grand Prix': 'Avusturya Grand Prix',
	'British Grand Prix': 'Britanya Grand Prix',
	'Belgian Grand Prix': 'Belçika Grand Prix',
	'Hungarian Grand Prix': 'Macaristan Grand Prix',
	'Dutch Grand Prix': 'Hollanda Grand Prix',
	'Italian Grand Prix': 'İtalya Grand Prix',
	'Spanish Grand Prix': 'İspanya Grand Prix',
	'Azerbaijan Grand Prix': 'Azerbaycan Grand Prix',
	'Singapore Grand Prix': 'Singapur Grand Prix',
	'United States Grand Prix': 'ABD Grand Prix',
	'Mexico City Grand Prix': 'Meksiko Grand Prix',
	'Brazilian Grand Prix': 'Brezilya Grand Prix',
	'Las Vegas Grand Prix': 'Las Vegas Grand Prix',
	'Qatar Grand Prix': 'Katar Grand Prix',
	'Abu Dhabi Grand Prix': 'Abu Dabi Grand Prix',
	'São Paulo Grand Prix': 'São Paulo Grand Prix',
	'Turkish Grand Prix': 'Türkiye Grand Prix',
};

/** Localized race name; falls back to the English name */
export function localizedRaceName(name, locale) {
	return locale === 'tr' && RACE_NAMES_TR[name] ? RACE_NAMES_TR[name] : name;
}
