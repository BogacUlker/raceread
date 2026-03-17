import { api } from '$lib/api.js';

export async function load({ params, fetch }) {
	const id = params.id;

	// Critical endpoints - page cannot render without these
	const [raceInfo, laps, strategy] = await Promise.all([
		api(`/api/races/${id}`, fetch),
		api(`/api/races/${id}/laps`, fetch),
		api(`/api/races/${id}/strategy`, fetch),
	]);

	// Optional endpoints - page still loads if any of these fail
	const optionalResults = await Promise.allSettled([
		api(`/api/races/${id}/delta`, fetch),
		api(`/api/races/${id}/annotations`, fetch),
		api(`/api/races/${id}/energy/comparison`, fetch),
		api(`/api/races/${id}/pitstops`, fetch),
	]);

	const delta = optionalResults[0].status === 'fulfilled'
		? optionalResults[0].value
		: { drivers: [], matrix: [] };

	const annotations = optionalResults[1].status === 'fulfilled'
		? optionalResults[1].value
		: [];

	const energyComparison = optionalResults[2].status === 'fulfilled'
		? optionalResults[2].value
		: { entries: [] };

	const pitstops = optionalResults[3].status === 'fulfilled'
		? optionalResults[3].value
		: { drivers: [] };

	return { raceId: id, raceInfo, laps, strategy, delta, annotations, energyComparison, pitstops };
}
