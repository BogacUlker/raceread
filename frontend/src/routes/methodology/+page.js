import { api } from '$lib/api.js';

export async function load({ fetch }) {
	const [races, classicList] = await Promise.all([
		api('/api/races', fetch).catch(() => []),
		api('/api/classics', fetch).catch(() => []),
	]);
	// the classics registry has no validation score - pull each race's info
	const classics = await Promise.all(
		classicList.map((c) => api(`/api/races/${c.id}`, fetch).catch(() => c))
	);
	return {
		races,
		classics,
		metaTitle: 'Metodoloji - RaceRead',
		metaDescription: 'How RaceRead infers F1 energy deployment from public telemetry, and how much to trust it.',
	};
}
