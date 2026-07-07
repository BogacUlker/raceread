<script>
	import { t, locale } from '$lib/i18n/index.js';
	import { localizedRaceName } from '$lib/constants.js';
	import { selectedEnergyDriver } from '$lib/stores/race.js';
	import EnergyTimeline from '$lib/components/charts/EnergyTimeline.svelte';
	import EnergyBars from '$lib/components/charts/EnergyBars.svelte';
	import EnergyDuel from '$lib/components/charts/EnergyDuel.svelte';
	import ClipMap from '$lib/components/charts/ClipMap.svelte';

	let { data } = $props();
	let raceId = $derived(data.raceId);
	let raceInfo = $derived(data.raceInfo);
	let laps = $derived(data.laps);
	let circuit = $derived(data.circuit);
	let energyComparison = $derived(data.energyComparison);

	// sorted by finishing order so selectors and duel defaults make sense
	let driverList = $derived(laps.map((d) => {
		const last = d.laps.filter((l) => l.position != null).at(-1);
		const pos = last?.position ?? 99;
		const isDNF = d.laps.length < (raceInfo.total_laps || 58) * 0.9;
		return { driver: d.driver, team: d.team, _pos: isDNF ? 100 + pos : pos };
	}).sort((a, b) => a._pos - b._pos));
	let runnerUp = $derived(driverList.find((d) => d.driver !== (data.focusDriver || raceInfo.winner))?.driver || '');

	// deep link: /energy?driver=XXX focuses timeline + duel
	const focus = data.focusDriver;
	$effect(() => {
		if (focus && laps.some((d) => d.driver === focus)) selectedEnergyDriver.set(focus);
	});

	function gpName(name) {
		if (!name) return '';
		const n = localizedRaceName(name, $locale);
		const parts = n.split('Grand Prix');
		if (parts.length === 2) return parts[0].toLocaleUpperCase($locale === 'tr' ? 'tr' : 'en') + 'GRAND PRIX';
		return n.toUpperCase();
	}
</script>

<svelte:head>
	<title>Energy - {raceInfo.name} - RaceRead</title>
</svelte:head>

<div class="en">
	<div class="en__header">
		<a href="/race/{raceId}" class="en__back">&larr; {gpName(raceInfo.name)}</a>
		<h1 class="en__title">{$t('energy.room_title')}</h1>
		<p class="en__sub">{$t('charts.inferred')} &middot; {raceInfo.circuit} &middot; {raceInfo.date}</p>
	</div>

	<div class="en__grid">
		<EnergyTimeline {raceId} drivers={driverList} defaultDriver={focus || raceInfo.winner} confidence={raceInfo.validation_confidence} />
		<div class="en__row">
			<EnergyDuel {raceId} drivers={driverList} d1init={focus || raceInfo.winner} d2init={runnerUp} totalLaps={raceInfo.total_laps} />
			<ClipMap {raceId} {circuit} confidence={raceInfo.validation_confidence} />
		</div>
		<EnergyBars entries={energyComparison.entries || []} />
	</div>
</div>

<style>
	.en {
		position: fixed; inset: 0; z-index: 200;
		overflow-y: auto; background: var(--bg-primary); color: var(--text-primary);
		font-family: var(--font-body); -webkit-font-smoothing: antialiased;
		padding: 1.5rem 2rem 3rem;
	}
	.en :global(*) { border-radius: 0 !important; }
	.en :global(.chart-card) {
		border: none !important;
		border-left: 2px solid transparent !important;
		background: var(--bg-secondary) !important;
		transition: border-color .25s !important;
	}
	.en :global(.chart-card:hover) { border-left-color: var(--accent) !important; }
	.en :global(.chart-card__title) {
		font-family: var(--font-heading) !important;
		text-transform: uppercase; letter-spacing: .03em; font-size: 16px !important;
	}

	.en__header { margin-bottom: 1.25rem; }
	.en__back { font-family: var(--font-mono); font-size: 11px; color: var(--accent-text); text-decoration: none; letter-spacing: .08em; }
	.en__back:hover { text-decoration: none; opacity: .8; }
	.en__title { font-family: var(--font-heading); font-size: 28px; font-weight: 700; text-transform: uppercase; margin-top: .5rem; }
	.en__sub { font-family: var(--font-mono); font-size: 10px; color: var(--text-muted); letter-spacing: .1em; text-transform: uppercase; margin-top: 2px; }

	.en__grid { display: flex; flex-direction: column; gap: 1.5rem; }
	.en__row { display: grid; grid-template-columns: 3fr 2fr; gap: 2px; align-items: start; }

	@media (max-width: 1000px) {
		.en__row { grid-template-columns: 1fr; }
		.en { padding: 1rem; }
	}
</style>
