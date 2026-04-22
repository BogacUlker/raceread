import { writable, derived } from 'svelte/store';
import tr from './tr.json';
import en from './en.json';

const translations = { tr, en };

/** Read saved locale from localStorage, default to 'tr' */
function getInitialLocale() {
	if (typeof window !== 'undefined') {
		const saved = localStorage.getItem('raceread-locale');
		if (saved === 'tr' || saved === 'en') return saved;
	}
	return 'en';
}

/** Current locale: 'tr' or 'en' */
export const locale = writable(getInitialLocale());

/** Persist locale changes to localStorage and update <html lang> */
if (typeof window !== 'undefined') {
	locale.subscribe((l) => {
		localStorage.setItem('raceread-locale', l);
		document.documentElement.lang = l;
	});
}

/**
 * Derived translation function.
 * Usage: $t('charts.pace') -> "Race Pace" or "Yaris Temposu"
 */
export const t = derived(locale, ($locale) => {
	/** @param {string} key */
	return (key) => {
		const keys = key.split('.');
		let val = translations[$locale];
		for (const k of keys) {
			val = val?.[k];
		}
		return val || key;
	};
});
