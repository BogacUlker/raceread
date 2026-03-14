<!--
	Broadcaster Mode - full-screen, auto-cycling charts with keyboard controls.
	Arrow keys: prev/next chart. Space: pause. ESC: exit.
-->
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

	// Strategy sorting
	let finalPosMap = $derived(
		Object.fromEntries(
			laps.map(d => {
				const lastLap = d.laps.filter(l => l.position != null).at(-1);
				return [d.driver, lastLap?.position ?? 99];
			})
		)
	);

	let strategySorted = $derived(
		[...(strategy.drivers || [])].sort((a, b) => (finalPosMap[a.driver] ?? 99) - (finalPosMap[b.driver] ?? 99))
	);

	// Default select all drivers
	$effect(() => {
		if (laps.length > 0) {
			selectedDrivers.set(laps.map(d => d.driver));
		}
	});

	// VSC laps
	let vscLaps = $state([]);
	async function loadVscLaps() {
		try {
			const vscData = await api(`/api/races/${raceId}/energy/vsc`);
			vscLaps = vscData.vsc_laps || [];
		} catch { vscLaps = []; }
	}
	loadVscLaps();

	// Chart cycling
	const CHARTS = ['pace', 'strategy', 'energy', 'speed-trace', 'track-map'];
	const CHART_LABELS = {
		pace: 'Race Pace',
		strategy: 'Strategy Timeline',
		energy: 'Energy Profile',
		'speed-trace': 'Speed Trace',
		'track-map': 'Track Map',
	};

	let activeChart = $state(0);
	let autoCycle = $state(true);
	let showOverlay = $state(false);
	let overlayTimeout = $state(null);
	let cycleInterval = $state(null);

	const CYCLE_MS = 18000; // 18 seconds per chart

	function startCycle() {
		stopCycle();
		cycleInterval = setInterval(() => {
			if (autoCycle) {
				activeChart = (activeChart + 1) % CHARTS.length;
			}
		}, CYCLE_MS);
	}

	function stopCycle() {
		if (cycleInterval) clearInterval(cycleInterval);
	}

	function nextChart() {
		activeChart = (activeChart + 1) % CHARTS.length;
	}

	function prevChart() {
		activeChart = (activeChart - 1 + CHARTS.length) % CHARTS.length;
	}

	function handleKeydown(e) {
		switch (e.key) {
			case 'ArrowRight': nextChart(); break;
			case 'ArrowLeft': prevChart(); break;
			case ' ':
				e.preventDefault();
				autoCycle = !autoCycle;
				break;
			case 'Escape':
				goto(`/race/${raceId}`);
				break;
		}
	}

	function handleMouseMove() {
		showOverlay = true;
		if (overlayTimeout) clearTimeout(overlayTimeout);
		overlayTimeout = setTimeout(() => { showOverlay = false; }, 3000);
	}

	onMount(() => {
		startCycle();
		return () => stopCycle();
	});
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="broadcast" onmousemove={handleMouseMove}>
	<!-- Top bar -->
	<div class="broadcast__topbar">
		<span class="broadcast__race-name">{raceInfo.name}</span>
		<span class="broadcast__chart-name">{CHART_LABELS[CHARTS[activeChart]]}</span>
		<span class="broadcast__cycle-indicator">
			{autoCycle ? '▶' : '⏸'}
			{activeChart + 1}/{CHARTS.length}
		</span>
	</div>

	<!-- Chart area -->
	<div class="broadcast__chart">
		{#if CHARTS[activeChart] === 'pace'}
			<PaceChart
				{laps}
				selectedDrivers={$selectedDrivers}
				{vscLaps}
				annotations={[]}
				{strategy}
			/>
		{:else if CHARTS[activeChart] === 'strategy'}
			<StrategyTimeline
				drivers={strategySorted}
				totalLaps={raceInfo.total_laps}
				{vscLaps}
			/>
		{:else if CHARTS[activeChart] === 'energy'}
			<EnergyBars entries={energyComparison.entries || []} />
		{:else if CHARTS[activeChart] === 'speed-trace'}
			<SpeedTrace {raceId} drivers={driverList} {circuit} totalLaps={raceInfo?.total_laps || 58} />
		{:else if CHARTS[activeChart] === 'track-map'}
			<TrackMap {raceId} drivers={driverList} {circuit} totalLaps={raceInfo?.total_laps || 58} />
		{/if}
	</div>

	<!-- Floating overlay (shows on hover) -->
	{#if showOverlay}
		<div class="broadcast__overlay">
			<div class="broadcast__overlay-pills">
				{#each CHARTS as chart, i}
					<button
						class="broadcast__overlay-pill"
						class:active={activeChart === i}
						onclick={() => { activeChart = i; }}
					>
						{CHART_LABELS[chart]}
					</button>
				{/each}
			</div>
			<div class="broadcast__overlay-controls">
				<button onclick={prevChart}>◀</button>
				<button onclick={() => { autoCycle = !autoCycle; }}>
					{autoCycle ? '⏸' : '▶'}
				</button>
				<button onclick={nextChart}>▶</button>
				<button onclick={() => goto(`/race/${raceId}`)}>✕</button>
			</div>
		</div>
	{/if}
</div>

<style>
	.broadcast {
		width: 100vw;
		height: 100vh;
		display: flex;
		flex-direction: column;
		background: var(--bg-primary);
		overflow: hidden;
		--broadcast-font-scale: 1.15;
		font-size: calc(1rem * var(--broadcast-font-scale));
	}
	.broadcast__topbar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 12px 24px;
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border);
		font-family: var(--font-mono);
		flex-shrink: 0;
	}
	.broadcast__race-name {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
	}
	.broadcast__chart-name {
		font-size: 14px;
		color: var(--text-secondary);
	}
	.broadcast__cycle-indicator {
		font-size: 12px;
		color: var(--text-muted);
	}
	.broadcast__chart {
		flex: 1;
		padding: 24px;
		overflow: auto;
	}
	.broadcast__overlay {
		position: fixed;
		bottom: 20px;
		left: 50%;
		transform: translateX(-50%);
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: 10px 16px;
		display: flex;
		align-items: center;
		gap: 16px;
		z-index: 100;
		animation: fadeIn 0.2s;
	}
	@keyframes fadeIn {
		from { opacity: 0; transform: translateX(-50%) translateY(10px); }
		to { opacity: 1; transform: translateX(-50%) translateY(0); }
	}
	.broadcast__overlay-pills {
		display: flex;
		gap: 4px;
	}
	.broadcast__overlay-pill {
		font-family: var(--font-mono);
		font-size: 11px;
		padding: 4px 10px;
		border: 1px solid var(--border);
		border-radius: 999px;
		background: transparent;
		color: var(--text-muted);
		cursor: pointer;
	}
	.broadcast__overlay-pill.active {
		background: var(--bg-secondary);
		color: var(--text-primary);
		border-color: var(--text-muted);
	}
	.broadcast__overlay-controls {
		display: flex;
		gap: 4px;
	}
	.broadcast__overlay-controls button {
		font-size: 14px;
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		color: var(--text-secondary);
		cursor: pointer;
		padding: 4px 8px;
	}
	.broadcast__overlay-controls button:hover {
		color: var(--text-primary);
		border-color: var(--text-muted);
	}
</style>
