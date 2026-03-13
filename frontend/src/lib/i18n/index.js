import { writable, derived } from 'svelte/store';
import tr from './tr.json';
import en from './en.json';

const translations = { tr, en };

/** Current locale: 'tr' or 'en' */
export const locale = writable('tr');

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
