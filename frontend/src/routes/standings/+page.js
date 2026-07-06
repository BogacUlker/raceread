import { api } from '$lib/api.js';

export async function load({ fetch }) {
	const standings = await api('/api/standings', fetch);

	let calendar = [];
	try {
		calendar = await api('/api/calendar', fetch);
	} catch (e) { /* chart falls back to round numbers */ }

	return {
		standings,
		calendar,
		metaTitle: '2026 Championship Standings - RaceRead',
		metaDescription:
			'2026 Formula 1 championship standings: driver and constructor points, wins, and round-by-round title progression.',
	};
}
