import { api } from '$lib/api.js';

export async function load({ params, fetch }) {
	const { id, d1, d2 } = params;

	const [raceInfo, laps, circuit, strategy, energyComparison] = await Promise.all([
		api(`/api/races/${id}`, fetch),
		api(`/api/races/${id}/laps`, fetch),
		api(`/api/races/${id}/circuit`, fetch).catch(() => null),
		api(`/api/races/${id}/strategy`, fetch),
		api(`/api/races/${id}/energy/comparison`, fetch),
	]);

	return {
		raceId: id,
		d1: d1.toUpperCase(),
		d2: d2.toUpperCase(),
		raceInfo,
		laps,
		circuit,
		strategy,
		energyComparison,
	};
}
