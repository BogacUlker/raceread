<script>
	import { t, locale } from '$lib/i18n/index.js';
	import { localizedRaceName } from '$lib/constants.js';
	import SpeedTrace from '$lib/components/charts/SpeedTrace.svelte';
	import TrackMap from '$lib/components/charts/TrackMap.svelte';
	import TrafficAnalysis from '$lib/components/charts/TrafficAnalysis.svelte';
	import GearMap from '$lib/components/charts/GearMap.svelte';

	let { data } = $props();
	let raceId = $derived(data.raceId);
	let raceInfo = $derived(data.raceInfo);
	let laps = $derived(data.laps);
	let circuit = $derived(data.circuit);
	let traffic = $derived(data.traffic);

	// sorted by finishing order (same convention as the dashboard)
	let driverList = $derived(laps.map((d) => {
		const last = d.laps.filter((l) => l.position != null).at(-1);
		const pos = last?.position ?? 99;
		const isDNF = d.laps.length < (raceInfo.total_laps || 58) * 0.9;
		return { driver: d.driver, team: d.team, _pos: isDNF ? 100 + pos : pos };
	}).sort((a, b) => a._pos - b._pos));

	function gpName(name) {
		if (!name) return '';
		const n = localizedRaceName(name, $locale);
		const parts = n.split('Grand Prix');
		if (parts.length === 2) return parts[0].toLocaleUpperCase($locale === 'tr' ? 'tr' : 'en') + 'GRAND PRIX';
		return n.toUpperCase();
	}
</script>

<svelte:head>
	<title>Telemetry - {raceInfo.name} - RaceRead</title>
</svelte:head>

<div class="tm">
	<div class="tm__header">
		<a href="/race/{raceId}" class="tm__back">&larr; {gpName(raceInfo.name)}</a>
		<h1 class="tm__title">{$t('telemetry.room_title')}</h1>
		<p class="tm__sub">{raceInfo.circuit} &middot; {raceInfo.date}</p>
	</div>

	<div class="tm__grid">
		<SpeedTrace {raceId} drivers={driverList} {circuit} totalLaps={raceInfo?.total_laps || 58} />
		<TrackMap {raceId} drivers={driverList} {circuit} totalLaps={raceInfo?.total_laps || 58} />
		<GearMap {raceId} drivers={driverList} totalLaps={raceInfo?.total_laps || 58} />
		<TrafficAnalysis trafficData={traffic} loading={false} />
	</div>
</div>

<style>
	.tm {
		position: fixed; inset: 0; z-index: 200;
		overflow-y: auto; background: #0F1117; color: #E8E8ED;
		font-family: var(--font-body); -webkit-font-smoothing: antialiased;
		padding: 1.5rem 2rem 3rem;
	}
	.tm :global(*) { border-radius: 0 !important; }
	.tm :global(.chart-card) {
		border: none !important;
		border-left: 2px solid transparent !important;
		background: #1A1D27 !important;
		transition: border-color .25s !important;
	}
	.tm :global(.chart-card:hover) { border-left-color: #E24B4A !important; }
	.tm :global(.chart-card__title) {
		font-family: var(--font-heading) !important;
		text-transform: uppercase; letter-spacing: .03em; font-size: 16px !important;
	}

	.tm__header { margin-bottom: 1.25rem; }
	.tm__back { font-family: var(--font-mono); font-size: 11px; color: #E24B4A; text-decoration: none; letter-spacing: .08em; }
	.tm__back:hover { text-decoration: none; opacity: .8; }
	.tm__title { font-family: var(--font-heading); font-size: 28px; font-weight: 700; text-transform: uppercase; margin-top: .5rem; }
	.tm__sub { font-family: var(--font-mono); font-size: 10px; color: #7D8794; letter-spacing: .1em; text-transform: uppercase; margin-top: 2px; }

	.tm__grid { display: flex; flex-direction: column; gap: 1.5rem; }

	@media (max-width: 900px) { .tm { padding: 1rem; } }
</style>
