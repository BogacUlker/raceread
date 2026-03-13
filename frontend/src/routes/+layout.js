import { api } from '$lib/api.js';

export async function load({ fetch }) {
	const races = await api('/api/races', fetch);
	return { races };
}
