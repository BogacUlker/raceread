import { api } from '$lib/api.js';

export async function load({ params, fetch }) {
	const id = params.id;

	const [raceInfo, laps, strategy, delta, energyComparison, circuit] = await Promise.all([
		api(`/api/races/${id}`, fetch),
		api(`/api/races/${id}/laps`, fetch),
		api(`/api/races/${id}/strategy`, fetch),
		api(`/api/races/${id}/delta`, fetch),
		api(`/api/races/${id}/energy/comparison`, fetch),
		api(`/api/races/${id}/circuit`, fetch).catch(() => null),
	]);

	return { raceId: id, raceInfo, laps, strategy, delta, energyComparison, circuit };
}
