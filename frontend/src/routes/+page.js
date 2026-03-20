import { api } from '$lib/api.js';

export async function load({ fetch }) {
	const races = await api('/api/races', fetch);

	// Fetch circuit outline for hero decoration (first race)
	let circuitOutline = [];
	try {
		const circuit = await api(`/api/races/${races[0].id}/circuit`, fetch);
		circuitOutline = circuit.outline || [];
	} catch (e) { /* ignore */ }

	return { races, circuitOutline };
}
