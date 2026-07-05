import { api } from '$lib/api.js';

export async function load({ params, fetch, url }) {
	const id = params.id;

	const [raceInfo, laps, circuit, strategy, energyComparison] = await Promise.all([
		api('/api/races/' + id, fetch),
		api('/api/races/' + id + '/laps', fetch),
		api('/api/races/' + id + '/circuit', fetch).catch(() => null),
		api('/api/races/' + id + '/strategy', fetch),
		api('/api/races/' + id + '/energy/comparison', fetch),
	]);

	return {
		raceId: id,
		raceInfo,
		laps,
		circuit,
		strategy,
		energyComparison,
		d1: url.searchParams.get('d1'),
		d2: url.searchParams.get('d2'),
		metaTitle: 'Compare - ' + raceInfo.name + ' - RaceRead',
		metaDescription: 'Head-to-head driver comparison for the ' + raceInfo.name + ': lap times, sectors, speed trace and energy deployment.',
	};
}
