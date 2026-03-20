import { api } from '$lib/api.js';

export async function load({ params, fetch }) {
	const id = params.id;

	const [raceInfo, laps, strategy, races] = await Promise.all([
		api(`/api/races/${id}`, fetch),
		api(`/api/races/${id}/laps`, fetch),
		api(`/api/races/${id}/strategy`, fetch),
		api('/api/races', fetch),
	]);

	const optionalResults = await Promise.allSettled([
		api(`/api/races/${id}/delta`, fetch),
		api(`/api/races/${id}/annotations`, fetch),
		api(`/api/races/${id}/energy/comparison`, fetch),
		api(`/api/races/${id}/pitstops`, fetch),
		api(`/api/races/${id}/energy/vsc`, fetch),
		api(`/api/races/${id}/circuit`, fetch),
		api(`/api/races/${id}/traffic`, fetch),
	]);

	const delta = optionalResults[0].status === 'fulfilled' ? optionalResults[0].value : { drivers: [], matrix: [] };
	const annotations = optionalResults[1].status === 'fulfilled' ? optionalResults[1].value : [];
	const energyComparison = optionalResults[2].status === 'fulfilled' ? optionalResults[2].value : { entries: [] };
	const pitstops = optionalResults[3].status === 'fulfilled' ? optionalResults[3].value : { drivers: [] };
	const vscData = optionalResults[4].status === 'fulfilled' ? optionalResults[4].value : { vsc_laps: [], sc_laps: [] };
	const circuit = optionalResults[5].status === 'fulfilled' ? optionalResults[5].value : null;
	const traffic = optionalResults[6].status === 'fulfilled' ? optionalResults[6].value : null;

	return { raceId: id, raceInfo, laps, strategy, delta, annotations, energyComparison, pitstops, races, vscData, circuit, traffic };
}
