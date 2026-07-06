import { api } from '$lib/api.js';

export async function load({ params, fetch, url }) {
	const id = params.id;

	const [raceInfo, laps, energyComparison, circuit] = await Promise.all([
		api(`/api/races/${id}`, fetch),
		api(`/api/races/${id}/laps`, fetch),
		api(`/api/races/${id}/energy/comparison`, fetch).catch(() => ({ entries: [] })),
		api(`/api/races/${id}/circuit`, fetch).catch(() => null),
	]);

	return {
		raceId: id,
		raceInfo,
		laps,
		energyComparison,
		circuit,
		focusDriver: (url.searchParams.get('driver') || '').toUpperCase() || null,
		metaTitle: 'Energy - ' + raceInfo.name + ' - RaceRead',
		metaDescription:
			'Inferred energy analysis for the ' + raceInfo.name +
			': lap-by-lap deployment, driver duels and the clip map of ' + raceInfo.circuit + '.',
	};
}
