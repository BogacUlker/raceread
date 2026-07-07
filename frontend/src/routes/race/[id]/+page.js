import { api } from '$lib/api.js';

export async function load({ params, fetch }) {
	const id = params.id;

	const [raceInfo, laps, strategy, races] = await Promise.all([
		api(`/api/races/${id}`, fetch),
		api(`/api/races/${id}/laps`, fetch),
		api(`/api/races/${id}/strategy`, fetch),
		api('/api/races', fetch),
	]);

	let calendar = [];
	try {
		calendar = await api('/api/calendar', fetch);
	} catch (e) { /* sidebar falls back to played-race count */ }

	let classics = [];
	try {
		classics = await api('/api/classics', fetch);
	} catch (e) { /* classic nav degrades to none */ }

	let story = null;
	try {
		story = await api(`/api/races/${id}/story`, fetch);
	} catch (e) { /* story block hides itself */ }

	let radio = null;
	try {
		radio = await api(`/api/races/${id}/radio`, fetch);
	} catch (e) { /* no radio for this race */ }

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

	return {
		raceId: id, raceInfo, laps, strategy, delta, annotations, energyComparison, pitstops, races, vscData, circuit, traffic, calendar, classics, story, radio,
		metaTitle: raceInfo.name + ' - RaceRead',
		metaDescription: raceInfo.name + ' (' + raceInfo.circuit + ', ' + raceInfo.date + '): lap-by-lap pace, strategy timeline, energy deployment and AI race insights.',
	};
}
