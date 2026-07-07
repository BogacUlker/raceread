<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n/index.js';
	import { selectedDrivers } from '$lib/stores/race.js';
	import { TEAM_COLORS } from '$lib/constants.js';
	import { api } from '$lib/api.js';

	import PaceChart from '$lib/components/charts/PaceChart.svelte';
	import StrategyTimeline from '$lib/components/charts/StrategyTimeline.svelte';
	import EnergyBars from '$lib/components/charts/EnergyBars.svelte';
	import SpeedTrace from '$lib/components/charts/SpeedTrace.svelte';
	import TrackMap from '$lib/components/charts/TrackMap.svelte';

	let { data } = $props();

	let raceId = $derived(data.raceId);
	let raceInfo = $derived(data.raceInfo);
	let laps = $derived(data.laps);
	let strategy = $derived(data.strategy);
	let delta = $derived(data.delta);
	let energyComparison = $derived(data.energyComparison);
	let circuit = $derived(data.circuit);

	let driverList = $derived(laps.map(d => ({ driver: d.driver, team: d.team })));

	let finalPosMap = $derived(Object.fromEntries(laps.map(d => {
		const lastLap = d.laps.filter(l => l.position != null).at(-1);
		return [d.driver, lastLap?.position ?? 99];
	})));

	let strategySorted = $derived(
		[...(strategy.drivers || [])].sort((a, b) => (finalPosMap[a.driver] ?? 99) - (finalPosMap[b.driver] ?? 99))
	);

	// Broadcast defaults to the top 6 finishers; "ALL" shows the full field
	let showAll = $state(false);
	let topSix = $derived(
		laps.map(d => ({ driver: d.driver, pos: finalPosMap[d.driver] ?? 99 }))
			.sort((a, b) => a.pos - b.pos)
			.slice(0, 6)
			.map(d => d.driver)
	);
	$effect(() => {
		if (laps.length > 0) {
			selectedDrivers.set(showAll ? laps.map(d => d.driver) : topSix);
		}
	});

	let vscLaps = $state([]);
	let scLaps = $state([]);
	if (typeof window !== 'undefined') {
		api(`/api/races/${raceId}/energy/vsc`).then(d => {
			vscLaps = d.vsc_laps || []; scLaps = d.sc_laps || [];
		}).catch(() => {});
	}

	const CHARTS = ['pace', 'strategy', 'energy', 'speed-trace', 'track-map'];
	let CHART_LABELS = $derived({
		pace: $t('charts.pace'),
		strategy: $t('charts.strategy'),
		energy: $t('charts.energy_bars'),
		'speed-trace': $t('charts.speed_trace'),
		'track-map': $t('charts.track_map'),
	});

	let activeChart = $state(0);

	// Auto-cycle through views every 15s until the user takes over
	let auto = $state(true);
	$effect(() => {
		if (!auto) return;
		const id = setInterval(() => {
			activeChart = (activeChart + 1) % CHARTS.length;
		}, 15000);
		return () => clearInterval(id);
	});
	function selectChart(i) {
		activeChart = i;
		auto = false;
	}

	// Uppercase race name with proper GRAND PRIX
	function gpName(name) {
		if (!name) return '';
		const parts = name.split('Grand Prix');
		if (parts.length === 2) return parts[0].toUpperCase() + 'GRAND PRIX';
		return name.toUpperCase();
	}

	function handleKeydown(e) {
		if (e.key === 'Escape') goto(`/race/${raceId}`);
		if (e.key === 'ArrowRight') selectChart((activeChart + 1) % CHARTS.length);
		if (e.key === 'ArrowLeft') selectChart((activeChart - 1 + CHARTS.length) % CHARTS.length);
	}
</script>

<svelte:head>
	<title>Broadcast - {raceInfo.name} - RaceRead</title>
</svelte:head>

<svelte:window onkeydown={handleKeydown} />

<div class="bc">
	<!-- Top bar -->
	<div class="bc__topbar">
		<div class="bc__left">
			<a href="/race/{raceId}" class="bc__exit" title="ESC">
				<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M12 4L4 12M4 4l8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
			</a>
			<span class="bc__race">{gpName(raceInfo.name)}</span>
		</div>
		<span class="bc__active-label">{CHART_LABELS[CHARTS[activeChart]]}</span>
		<div class="bc__controls">
			<button class="bc__ctl" class:bc__ctl--on={!showAll} onclick={() => showAll = !showAll}>
				{showAll ? 'ALL' : 'TOP 6'}
			</button>
			<button class="bc__ctl" class:bc__ctl--on={auto} onclick={() => auto = !auto} title="Auto-cycle views">
				AUTO {auto ? 'ON' : 'OFF'}
			</button>
			<span class="bc__counter">{activeChart + 1} / {CHARTS.length}</span>
		</div>
	</div>

	<!-- Chart area -->
	<div class="bc__chart">
		{#if CHARTS[activeChart] === 'pace'}
			<PaceChart {laps} selectedDrivers={$selectedDrivers} {vscLaps} {scLaps} annotations={[]} {strategy} />
		{:else if CHARTS[activeChart] === 'strategy'}
			<StrategyTimeline drivers={strategySorted.filter(d => $selectedDrivers.includes(d.driver))} totalLaps={raceInfo.total_laps} {vscLaps} {scLaps} />
		{:else if CHARTS[activeChart] === 'energy'}
			<EnergyBars entries={(energyComparison.entries || []).filter(e => $selectedDrivers.includes(e.driver))} />
		{:else if CHARTS[activeChart] === 'speed-trace'}
			<SpeedTrace {raceId} drivers={driverList} {circuit} totalLaps={raceInfo?.total_laps || 58} />
		{:else if CHARTS[activeChart] === 'track-map'}
			<TrackMap {raceId} drivers={driverList} {circuit} totalLaps={raceInfo?.total_laps || 58} />
		{/if}
	</div>

	<!-- Bottom: chart selector pills (always visible) -->
	<div class="bc__bottom">
		{#each CHARTS as chart, i}
			<button class="bc__pill" class:bc__pill--active={activeChart === i} onclick={() => selectChart(i)}>
				{CHART_LABELS[chart]}
			</button>
		{/each}
	</div>
</div>

<style>
	.bc {
		width: 100vw; height: 100vh;
		display: flex; flex-direction: column;
		background: var(--bg-primary); color: var(--text-primary);
		font-family: var(--font-body);
		-webkit-font-smoothing: antialiased;
		overflow: hidden;
		--fh: var(--font-heading);
		--fm: var(--font-mono);
		--ac: var(--accent);
		--bg2: var(--bg-secondary);
		--brd: var(--border);
		--tm: #6B7280;
	}
	.bc :global(*) { border-radius: 0 !important; }
	.bc :global(.chart-card) { border-radius: 0 !important; border: none !important; background: var(--bg2) !important; }
	.bc :global(.chart-card__title) { font-family: var(--fh) !important; text-transform: uppercase; letter-spacing: .03em; font-size: 24px !important; }
	/* broadcast fills the screen with the chart */
	.bc :global(.pace-wrapper .chart-container) { height: calc(100vh - 320px) !important; min-height: 340px; }
	.bc__chart > :global(*) { min-height: 100%; }

	.bc__controls { display: flex; align-items: center; gap: 8px; }
	.bc__ctl {
		font-family: var(--fm); font-size: 10px; font-weight: 700; letter-spacing: .08em;
		padding: 5px 12px; background: none; border: 1px solid var(--brd);
		color: var(--tm); cursor: pointer; transition: all .15s; text-transform: uppercase;
	}
	.bc__ctl:hover { color: var(--text-primary); border-color: #6B7280; }
	.bc__ctl--on { background: var(--ac); color: #fff; border-color: var(--ac); font-style: italic; }

	/* Top bar */
	.bc__topbar {
		display: flex; align-items: center; justify-content: space-between;
		padding: 0 1.5rem; height: 48px; flex-shrink: 0;
		background: var(--bg2); border-bottom: 1px solid rgba(46,50,64,.5);
	}
	.bc__left { display: flex; align-items: center; gap: 1rem; }
	.bc__exit {
		display: flex; align-items: center; justify-content: center;
		width: 28px; height: 28px; color: var(--tm);
		border: 1px solid var(--brd); text-decoration: none;
		transition: color .15s, border-color .15s;
	}
	.bc__exit:hover { color: var(--ac); border-color: var(--ac); text-decoration: none; }
	.bc__race { font-family: var(--fh); font-size: 15px; font-weight: 900; font-style: italic; letter-spacing: .02em; }
	.bc__active-label { font-family: var(--fh); font-size: 13px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: .06em; }
	.bc__counter { font-family: var(--fm); font-size: 11px; color: var(--tm); }

	/* Chart area */
	.bc__chart { flex: 1; padding: 1.25rem 1.5rem; overflow: auto; }

	/* Bottom pills */
	.bc__bottom {
		display: flex; align-items: center; justify-content: center;
		gap: 2px; padding: .6rem 1.5rem; flex-shrink: 0;
		background: var(--bg2); border-top: 1px solid rgba(46,50,64,.5);
	}
	.bc__pill {
		font-family: var(--fm); font-size: 11px;
		padding: 7px 16px; background: none;
		border: 1px solid var(--brd); color: var(--tm);
		cursor: pointer; transition: all .15s;
		text-transform: uppercase; letter-spacing: .04em;
	}
	.bc__pill:hover { color: var(--text-primary); border-color: #6B7280; }
	.bc__pill--active {
		background: var(--ac); color: #fff;
		border-color: var(--ac); font-weight: 900; font-style: italic;
	}

	@media (max-width: 640px) {
		.bc__topbar { padding: 0 .75rem; }
		.bc__chart { padding: .75rem; }
		.bc__bottom { padding: .5rem .75rem; gap: 2px; }
		.bc__pill { padding: 6px 10px; font-size: 10px; }
		.bc__race { font-size: 12px; }
	}
</style>
