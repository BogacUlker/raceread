import { api } from '$lib/api.js';

export async function load({ params, fetch }) {
	const id = params.id;

	const [raceInfo, laps, strategy, delta, annotations, energyComparison] = await Promise.all([
		api(`/api/races/${id}`, fetch),
		api(`/api/races/${id}/laps`, fetch),
		api(`/api/races/${id}/strategy`, fetch),
		api(`/api/races/${id}/delta`, fetch),
		api(`/api/races/${id}/annotations`, fetch),
		api(`/api/races/${id}/energy/comparison`, fetch),
	]);

	return { raceId: id, raceInfo, laps, strategy, delta, annotations, energyComparison };
}
