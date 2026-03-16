import { writable } from 'svelte/store';
import { browser } from '$app/environment';

const STORAGE_KEY = 'raceread:collapsed';

const SECTIONS = ['insights', 'pace', 'strategy', 'pit-stops', 'energy', 'energy-timeline', 'speed-trace', 'track-map', 'traffic'];

const QUALIFYING_SECTIONS = ['qualifying-results', 'sector-comparison', 'ideal-laps', 'qualifying-delta'];

function loadFromStorage() {
	if (!browser) return {};
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		return raw ? JSON.parse(raw) : {};
	} catch {
		return {};
	}
}

function saveToStorage(state) {
	if (!browser) return;
	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
	} catch {
		// ignore
	}
}

function createCollapsedSections() {
	const initial = loadFromStorage();
	const { subscribe, set, update } = writable(initial);

	return {
		subscribe,
		toggle(sectionId) {
			update((state) => {
				const next = { ...state, [sectionId]: !state[sectionId] };
				saveToStorage(next);
				return next;
			});
		},
		expandAll() {
			const next = {};
			saveToStorage(next);
			set(next);
		},
		collapseAll() {
			const next = Object.fromEntries(SECTIONS.map((s) => [s, true]));
			saveToStorage(next);
			set(next);
		}
	};
}

export const collapsedSections = createCollapsedSections();
export { SECTIONS, QUALIFYING_SECTIONS };
