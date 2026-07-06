import { api } from '$lib/api.js';

export async function load({ params, fetch }) {
	const id = params.id;

	const [raceInfo, laps, circuit, traffic] = await Promise.all([
		api(`/api/races/${id}`, fetch),
		api(`/api/races/${id}/laps`, fetch),
		api(`/api/races/${id}/circuit`, fetch).catch(() => null),
		api(`/api/races/${id}/traffic`, fetch).catch(() => null),
	]);

	return {
		raceId: id,
		raceInfo,
		laps,
		circuit,
		traffic,
		metaTitle: 'Telemetry - ' + raceInfo.name + ' - RaceRead',
		metaDescription:
			'Raw telemetry for the ' + raceInfo.name +
			': speed traces, animated track map and traffic analysis.',
	};
}
