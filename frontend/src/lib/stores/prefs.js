import { writable } from 'svelte/store';

/**
 * Favorite driver ("Pilotunu seç") - persisted in localStorage.
 * Empty string = no favorite.
 */
const KEY = 'raceread:favorite-driver';

const initial =
	typeof localStorage !== 'undefined' ? localStorage.getItem(KEY) || '' : '';

export const favoriteDriver = writable(initial);

favoriteDriver.subscribe((v) => {
	if (typeof localStorage === 'undefined') return;
	if (v) localStorage.setItem(KEY, v);
	else localStorage.removeItem(KEY);
});
