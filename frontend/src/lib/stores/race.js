import { writable } from 'svelte/store';

/** Currently selected drivers for multi-select filter */
export const selectedDrivers = writable([]);

/** Currently selected single driver (for energy timeline) */
export const selectedEnergyDriver = writable('');

/** Lap hovered in ANY chart - syncs vertical guide lines across charts */
export const hoveredLap = writable(null);

/** Driver hovered in ANY chart - highlights in PaceChart */
export const hoveredDriver = writable(null);

/** Driver clicked/pinned in PaceChart - stays highlighted */
export const pinnedDriver = writable(null);

/** Active session tab: 'race' or 'qualifying' */
export const activeSession = writable('race');
