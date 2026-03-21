import { api } from '$lib/api.js';

export async function load({ params, fetch }) {
	const { id, d1, d2 } = params;

	const [raceInfo, qualifyingTelemetry, circuit, races] = await Promise.all([
		api(`/api/races/${id}`, fetch),
		api(`/api/races/${id}/qualifying/telemetry?d1=${d1.toUpperCase()}&d2=${d2.toUpperCase()}`, fetch).catch(() => ({ drivers: [] })),
		api(`/api/races/${id}/circuit`, fetch).catch(() => null),
		api('/api/races', fetch).catch(() => []),
	]);

	return {
		raceId: id,
		d1: d1.toUpperCase(),
		d2: d2.toUpperCase(),
		raceInfo,
		qualifyingTelemetry,
		circuit,
		races,
	};
}
