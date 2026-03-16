import { api } from '$lib/api.js';

export async function load({ params, fetch }) {
	const { id, d1, d2 } = params;

	const [raceInfo, qualifyingTelemetry, circuit] = await Promise.all([
		api(`/api/races/${id}`, fetch),
		api(`/api/races/${id}/qualifying/telemetry?d1=${d1.toUpperCase()}&d2=${d2.toUpperCase()}`, fetch),
		api(`/api/races/${id}/circuit`, fetch).catch(() => null),
	]);

	return {
		raceId: id,
		d1: d1.toUpperCase(),
		d2: d2.toUpperCase(),
		raceInfo,
		qualifyingTelemetry,
		circuit,
	};
}
