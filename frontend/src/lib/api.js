const VITE_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Get the API base URL, using runtime env for SSR when available.
 * In Docker, SSR needs to reach backend via service name, not localhost.
 */
function getApiBase() {
	if (typeof window === 'undefined') {
		// SSR: use runtime env (set in docker-compose) or fall back to VITE_
		return process.env.API_URL_INTERNAL || VITE_API_URL;
	}
	return VITE_API_URL;
}

/**
 * Fetch JSON from the RaceRead API.
 * @param {string} path - API path (e.g., '/api/races')
 * @param {typeof fetch} [fetchFn] - Fetch function (SvelteKit's or browser's)
 */
export async function api(path, fetchFn = fetch) {
	const base = getApiBase();
	const res = await fetchFn(`${base}${path}`);
	if (!res.ok) {
		throw new Error(`API error ${res.status}: ${path}`);
	}
	return res.json();
}
