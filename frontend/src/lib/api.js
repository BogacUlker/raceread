const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Fetch JSON from the RaceRead API.
 * @param {string} path - API path (e.g., '/api/races')
 * @param {typeof fetch} [fetchFn] - Fetch function (SvelteKit's or browser's)
 */
export async function api(path, fetchFn = fetch) {
	const res = await fetchFn(`${API_BASE}${path}`);
	if (!res.ok) {
		throw new Error(`API error ${res.status}: ${path}`);
	}
	return res.json();
}
