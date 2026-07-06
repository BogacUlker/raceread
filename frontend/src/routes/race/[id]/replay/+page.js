import { api } from '$lib/api.js';

export async function load({ params, fetch, url }) {
	const id = params.id;

	const [raceInfo, laps, strategy, vscData] = await Promise.all([
		api(`/api/races/${id}`, fetch),
		api(`/api/races/${id}/laps`, fetch),
		api(`/api/races/${id}/strategy`, fetch).catch(() => ({ drivers: [] })),
		api(`/api/races/${id}/energy/vsc`, fetch).catch(() => ({ vsc_laps: [], sc_laps: [] })),
	]);

	const startLap = parseInt(url.searchParams.get('lap') || '1', 10) || 1;

	return {
		raceId: id,
		raceInfo,
		laps,
		strategy,
		vscData,
		startLap,
		metaTitle: 'Replay - ' + raceInfo.name + ' - RaceRead',
		metaDescription:
			'Scrub through the ' + raceInfo.name + ' lap by lap: running order, gaps, pit stops and safety cars.',
	};
}
