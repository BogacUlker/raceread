import { writable } from 'svelte/store';

/** Theme: 'dark' (default) or 'light' */
export const theme = writable('dark');
