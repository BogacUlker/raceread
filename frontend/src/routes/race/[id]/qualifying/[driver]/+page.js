import { api } from '$lib/api.js';

export async function load({ params, fetch }) {
	const { id, driver } = params;

	const [qualifying, raceInfo] = await Promise.all([
		api(`/api/races/${id}/qualifying`, fetch),
		api(`/api/races/${id}`, fetch),
	]);

	return {
		raceId: id,
		driverCode: driver.toUpperCase(),
		qualifying,
		raceInfo,
	};
}
