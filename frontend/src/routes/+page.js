import { api } from '$lib/api.js';

export async function load({ fetch }) {
	const races = await api('/api/races', fetch);

	// Season calendar (served from data/calendar.json, sourced from Jolpica)
	let calendar = [];
	try {
		calendar = await api('/api/calendar', fetch);
	} catch (e) { /* timeline hides itself when empty */ }

	// Fetch circuit outline for hero decoration (most recent race)
	let circuitOutline = [];
	const lastRace = races.length > 0 ? races[races.length - 1] : null;
	if (lastRace) {
		try {
			const circuit = await api('/api/races/' + lastRace.id + '/circuit', fetch);
			circuitOutline = circuit.outline || [];
		} catch (e) { /* ignore */ }
	}

	let classics = [];
	try {
		classics = await api('/api/classics', fetch);
	} catch (e) { /* shelf hides itself */ }

	return { races, circuitOutline, calendar, classics };
}
