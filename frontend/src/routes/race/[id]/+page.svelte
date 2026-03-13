<!--
	Race Dashboard - assembles all 7 MVP-1 charts.
	Responsive grid layout with driver filter and bilingual support.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { selectedDrivers } from '$lib/stores/race.js';
	import { TEAM_COLORS } from '$lib/constants.js';
	import { api } from '$lib/api.js';

	import DriverFilter from '$lib/components/layout/DriverFilter.svelte';
	import RaceInsightsPanel from '$lib/components/RaceInsightsPanel.svelte';
	import PaceChart from '$lib/components/charts/PaceChart.svelte';
	import SummarizedPace from '$lib/components/charts/SummarizedPace.svelte';
	import StrategyTimeline from '$lib/components/charts/StrategyTimeline.svelte';
	import EnergyBars from '$lib/components/charts/EnergyBars.svelte';
	import DeltaMatrix from '$lib/components/charts/DeltaMatrix.svelte';
	import EnergyTimeline from '$lib/components/charts/EnergyTimeline.svelte';

	let { data } = $props();

	let raceId = $derived(data.raceId);
	let raceInfo = $derived(data.raceInfo);
	let laps = $derived(data.laps);
	let strategy = $derived(data.strategy);
	let delta = $derived(data.delta);
	let annotations = $derived(data.annotations);
	let energyComparison = $derived(data.energyComparison);

	// Build driver list with teams from laps data
	let driverList = $derived(laps.map((d) => ({ driver: d.driver, team: d.team })));

	// Build teams map for delta matrix
	let teamsMap = $derived(Object.fromEntries(laps.map((d) => [d.driver, d.team])));

	// Final position map from laps data (for sorting)
	let finalPosMap = $derived(
		Object.fromEntries(
			laps.map((d) => {
				const lastLap = d.laps.filter((l) => l.position != null).at(-1);
				return [d.driver, lastLap?.position ?? 99];
			})
		)
	);

	// Strategy drivers sorted by race finish position
	let strategySorted = $derived(
		[...(strategy.drivers || [])].sort(
			(a, b) => (finalPosMap[a.driver] ?? 99) - (finalPosMap[b.driver] ?? 99)
		)
	);

	// Default: top 5 drivers by position on final lap
	let defaultSelected = $derived(
		laps
			.map((d) => {
				const lastLap = d.laps.filter((l) => l.position != null).at(-1);
				return { driver: d.driver, pos: lastLap?.position ?? 99 };
			})
			.sort((a, b) => a.pos - b.pos)
			.slice(0, 5)
			.map((d) => d.driver)
	);

	// Track whether defaults have been applied (so Clear can work)
	let initialized = $state(false);

	// Initialize selected drivers once on first load
	$effect(() => {
		if (!initialized && $selectedDrivers.length === 0 && defaultSelected.length > 0) {
			selectedDrivers.set(defaultSelected);
			initialized = true;
		}
	});

	// Get VSC laps (fetch from energy/vsc endpoint)
	let vscLaps = $state([]);

	async function loadVscLaps() {
		try {
			const vscData = await api(`/api/races/${raceId}/energy/vsc`);
			vscLaps = vscData.vsc_laps || [];
		} catch {
			vscLaps = [];
		}
	}

	loadVscLaps();
</script>

<svelte:head>
	<title>{raceInfo.name} - RaceRead</title>
</svelte:head>

<section class="dashboard">
	<!-- Race Info Header -->
	<div class="dashboard__header">
		<div class="dashboard__info">
			<h1 class="dashboard__title">{raceInfo.name}</h1>
			<div class="dashboard__meta">
				<span>{raceInfo.circuit}</span>
				<span class="sep">-</span>
				<span>{raceInfo.date}</span>
				<span class="sep">-</span>
				<span>{raceInfo.total_laps} {$t('race.laps')}</span>
				<span class="sep">-</span>
				<span class="winner">{$t('race.winner')}: {raceInfo.winner}</span>
			</div>
		</div>
	</div>

	<!-- Driver Filter -->
	<div class="dashboard__filter">
		<DriverFilter
			drivers={driverList}
			selected={$selectedDrivers}
			onchange={(v) => selectedDrivers.set(v)}
		/>
	</div>

	<!-- Race Insights -->
	<RaceInsightsPanel annotations={annotations.annotations || []} />

	<!-- Charts Grid -->
	<div class="dashboard__grid">
		<!-- Row 1: Pace Chart (wide) + Summarized Pace (sidebar) -->
		<div class="grid-row grid-row--pace">
			<div class="grid-cell grid-cell--wide">
				<PaceChart
					{laps}
					selectedDrivers={$selectedDrivers}
					{vscLaps}
					annotations={annotations.annotations || []}
					{strategy}
				/>
			</div>
			<div class="grid-cell grid-cell--sidebar">
				<SummarizedPace {laps} />
			</div>
		</div>

		<!-- Row 2: Strategy Timeline (full width) -->
		<div class="grid-row grid-row--full">
			<StrategyTimeline
				drivers={strategySorted}
				totalLaps={raceInfo.total_laps}
				{vscLaps}
			/>
		</div>

		<!-- Row 3: Energy Bars + Delta Matrix -->
		<div class="grid-row grid-row--split">
			<div class="grid-cell">
				<EnergyBars entries={energyComparison.entries || []} />
			</div>
			<div class="grid-cell">
				<DeltaMatrix
					drivers={delta.drivers || []}
					matrix={delta.matrix || []}
					teams={teamsMap}
				/>
			</div>
		</div>

		<!-- Row 4: Energy Timeline (full width, per-driver) -->
		<div class="grid-row grid-row--full">
			<EnergyTimeline
				{raceId}
				drivers={driverList}
				defaultDriver={raceInfo.winner}
			/>
		</div>
	</div>
</section>

<style>
	.dashboard {
		padding-top: var(--space-md);
	}
	.dashboard__header {
		margin-bottom: var(--space-lg);
	}
	.dashboard__title {
		font-family: var(--font-mono);
		font-size: 24px;
		font-weight: 700;
		letter-spacing: -0.02em;
		margin-bottom: var(--space-xs);
	}
	.dashboard__meta {
		display: flex;
		align-items: center;
		gap: var(--space-xs);
		font-size: 13px;
		color: var(--text-secondary);
	}
	.sep {
		color: var(--text-muted);
	}
	.winner {
		color: var(--accent);
		font-weight: 500;
	}
	.dashboard__filter {
		margin-bottom: var(--space-lg);
	}
	.dashboard__grid {
		display: flex;
		flex-direction: column;
		gap: var(--space-lg);
	}
	.grid-row--pace {
		display: grid;
		grid-template-columns: 2fr 1fr;
		gap: var(--space-lg);
	}
	.grid-row--full {
		/* full width */
	}
	.grid-row--split {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-lg);
	}

	/* Responsive */
	@media (max-width: 1200px) {
		.grid-row--pace {
			grid-template-columns: 1fr;
		}
		.grid-row--split {
			grid-template-columns: 1fr;
		}
	}

	@media (max-width: 768px) {
		.dashboard__title {
			font-size: 18px;
		}
		.dashboard__meta {
			flex-wrap: wrap;
		}
	}
</style>
