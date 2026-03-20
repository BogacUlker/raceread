import { api } from '$lib/api.js';

export async function load({ fetch }) {
	const races = await api('/api/races', fetch);

	// Fetch circuit outline for hero decoration (most recent race)
	let circuitOutline = [];
	const lastRace = races.length > 0 ? races[races.length - 1] : null;
	if (lastRace) {
		try {
			const circuit = await api('/api/races/' + lastRace.id + '/circuit', fetch);
			circuitOutline = circuit.outline || [];
		} catch (e) { /* ignore */ }
	}

	return { races, circuitOutline };
}
