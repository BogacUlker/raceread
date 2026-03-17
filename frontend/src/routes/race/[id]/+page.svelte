<!--
	Race Dashboard - assembles all 7 MVP-1 charts + qualifying session.
	Responsive grid layout with driver filter, collapsible sections, and bilingual support.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { get } from 'svelte/store';
	import { selectedDrivers, activeSession, showAnnotations } from '$lib/stores/race.js';
	import { collapsedSections } from '$lib/stores/dashboard.js';
	import { TEAM_COLORS } from '$lib/constants.js';
	import { api } from '$lib/api.js';

	import DriverFilter from '$lib/components/layout/DriverFilter.svelte';
	import SessionToggle from '$lib/components/layout/SessionToggle.svelte';
	import ChartNav from '$lib/components/layout/ChartNav.svelte';
	import RaceInsightsPanel from '$lib/components/RaceInsightsPanel.svelte';
	import PaceChart from '$lib/components/charts/PaceChart.svelte';
	import SummarizedPace from '$lib/components/charts/SummarizedPace.svelte';
	import StrategyTimeline from '$lib/components/charts/StrategyTimeline.svelte';
	import EnergyBars from '$lib/components/charts/EnergyBars.svelte';
	import DeltaMatrix from '$lib/components/charts/DeltaMatrix.svelte';
	import EnergyTimeline from '$lib/components/charts/EnergyTimeline.svelte';
	import QualifyingResults from '$lib/components/charts/QualifyingResults.svelte';
	import SectorComparison from '$lib/components/charts/SectorComparison.svelte';
	import QualifyingDelta from '$lib/components/charts/QualifyingDelta.svelte';
	import SpeedTrace from '$lib/components/charts/SpeedTrace.svelte';
	import TrackMap from '$lib/components/charts/TrackMap.svelte';
	import TrafficAnalysis from '$lib/components/charts/TrafficAnalysis.svelte';
	import PitStopStats from '$lib/components/charts/PitStopStats.svelte';
	import IdealLaps from '$lib/components/charts/IdealLaps.svelte';

	let { data } = $props();

	let raceId = $derived(data.raceId);
	let raceInfo = $derived(data.raceInfo);
	let laps = $derived(data.laps);
	let strategy = $derived(data.strategy);
	let delta = $derived(data.delta);
	let annotations = $derived(data.annotations);
	let energyComparison = $derived(data.energyComparison);
	let pitstops = $derived(data.pitstops);

	// Collapsed sections state
	let collapsed = $state({});
	$effect(() => { collapsed = get(collapsedSections); });

	// Active session state
	let session = $state('race');
	$effect(() => { session = get(activeSession); });

	// Qualifying data - lazy loaded on first tab switch
	let qualifyingData = $state(null);
	let qualifyingLoading = $state(false);
	let qualifyingError = $state(false);

	$effect(() => {
		if (session === 'qualifying' && qualifyingData === null && !qualifyingLoading) {
			loadQualifying();
		}
	});

	async function loadQualifying() {
		qualifyingLoading = true;
		qualifyingError = false;
		try {
			qualifyingData = await api(`/api/races/${raceId}/qualifying`);
		} catch {
			qualifyingError = true;
		} finally {
			qualifyingLoading = false;
		}
	}

	// Build driver list with teams from laps data
	let driverList = $derived(laps.map((d) => ({ driver: d.driver, team: d.team })));

	// Build teams map for delta matrix
	let teamsMap = $derived(Object.fromEntries(laps.map((d) => [d.driver, d.team])));

	// Final position map from laps data (for sorting)
	// DNF drivers (completed significantly fewer laps) sort below finishers
	let finalPosMap = $derived(
		Object.fromEntries(
			laps.map((d) => {
				const lastLap = d.laps.filter((l) => l.position != null).at(-1);
				const pos = lastLap?.position ?? 99;
				const completedLaps = d.laps.length;
				const isDNF = completedLaps < (raceInfo.total_laps || 58) * 0.9;
				return [d.driver, isDNF ? 100 + (raceInfo.total_laps - completedLaps) : pos];
			})
		)
	);

	// Strategy drivers sorted by race finish position
	let strategySorted = $derived(
		[...(strategy.drivers || [])].sort(
			(a, b) => (finalPosMap[a.driver] ?? 99) - (finalPosMap[b.driver] ?? 99)
		)
	);

	// Default: top 10 drivers by position on final lap
	let defaultSelected = $derived(
		laps
			.map((d) => {
				const lastLap = d.laps.filter((l) => l.position != null).at(-1);
				return { driver: d.driver, pos: lastLap?.position ?? 99 };
			})
			.sort((a, b) => a.pos - b.pos)
			.slice(0, 10)
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

	// Get VSC + SC laps (fetch from energy/vsc endpoint)
	let vscLaps = $state([]);
	let scLaps = $state([]);

	async function loadVscLaps() {
		try {
			const vscData = await api(`/api/races/${raceId}/energy/vsc`);
			vscLaps = vscData.vsc_laps || [];
			scLaps = vscData.sc_laps || [];
		} catch {
			vscLaps = [];
			scLaps = [];
		}
	}

	loadVscLaps();

	// Circuit data for speed trace + track map
	let circuitData = $state(null);

	async function loadCircuit() {
		try {
			circuitData = await api(`/api/races/${raceId}/circuit`);
		} catch {
			circuitData = null;
		}
	}

	loadCircuit();

	// Traffic analysis
	let trafficData = $state(null);
	let trafficLoading = $state(true);

	async function loadTraffic() {
		trafficLoading = true;
		try {
			// Add timeout to prevent indefinite loading state
			const timeoutPromise = new Promise((_, reject) =>
				setTimeout(() => reject(new Error('Traffic data timeout')), 10000)
			);
			trafficData = await Promise.race([
				api(`/api/races/${raceId}/traffic`),
				timeoutPromise
			]);
		} catch {
			trafficData = null;
		}
		trafficLoading = false;
	}

	loadTraffic();
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

	<!-- Session Toggle -->
	<SessionToggle />

	<!-- Driver Filter (race mode only) -->
	{#if session === 'race'}
		<div class="dashboard__toolbar">
			<div class="dashboard__filter">
				<DriverFilter
					drivers={driverList}
					selected={$selectedDrivers}
					onchange={(v) => selectedDrivers.set(v)}
				/>
			</div>
			<div class="dashboard__actions">
				<button
					class="dashboard__action-btn"
					class:active={$showAnnotations}
					onclick={() => showAnnotations.update(v => !v)}
				>
					{$t('annotations.toggle_label')}
					{$showAnnotations ? 'ON' : 'OFF'}
				</button>
				{#if driverList.length >= 2}
					<a href="/race/{raceId}/compare/{driverList[0].driver}/{driverList[1].driver}" class="dashboard__action-btn">
						{$t('charts.compare')}
					</a>
				{/if}
				<a href="/race/{raceId}/broadcast" class="dashboard__action-btn dashboard__action-btn--broadcast">
					{$t('charts.broadcast')}
				</a>
			</div>
		</div>
	{/if}

	<!-- Quick Nav -->
	<ChartNav />

	{#if session === 'race'}
		<!-- Race Insights -->
		<div id="section-insights" class="dashboard-section">
			<button class="section-toggle" onclick={() => collapsedSections.toggle('insights')}>
				<span class="chevron" class:rotated={collapsed['insights']}>&#9660;</span>
			</button>
			<div class="section-body" class:collapsed={collapsed['insights']}>
				{#if $showAnnotations}
				<RaceInsightsPanel annotations={$showAnnotations ? (annotations.annotations || []) : []} />
				{/if}
			</div>
		</div>

		<!-- Charts Grid -->
		<div class="dashboard__grid">
			<!-- Row 1: Pace Chart (wide) + Summarized Pace (sidebar) -->
			<div id="section-pace" class="dashboard-section">
				<button class="section-toggle" onclick={() => collapsedSections.toggle('pace')}>
					<span class="chevron" class:rotated={collapsed['pace']}>&#9660;</span>
				</button>
				<div class="section-body" class:collapsed={collapsed['pace']}>
					<div class="grid-row grid-row--pace">
						<div class="grid-cell grid-cell--wide">
							<PaceChart
								{laps}
								selectedDrivers={$selectedDrivers}
								{vscLaps}
								{scLaps}
								annotations={$showAnnotations ? (annotations.annotations || []) : []}
								{strategy}
							/>
						</div>
						<div class="grid-cell grid-cell--sidebar">
							<SummarizedPace {laps} />
						</div>
					</div>
				</div>
			</div>

			<!-- Row 2: Strategy Timeline (full width) -->
			<div id="section-strategy" class="dashboard-section">
				<button class="section-toggle" onclick={() => collapsedSections.toggle('strategy')}>
					<span class="chevron" class:rotated={collapsed['strategy']}>&#9660;</span>
				</button>
				<div class="section-body" class:collapsed={collapsed['strategy']}>
					<div class="grid-row grid-row--full">
						<StrategyTimeline
							drivers={strategySorted}
							totalLaps={raceInfo.total_laps}
							{vscLaps}
							{scLaps}
						/>
					</div>
				</div>
			</div>

			<!-- Row 2b: Pit Stop Stats (full width) -->
			<div id="section-pit-stops" class="dashboard-section">
				<button class="section-toggle" onclick={() => collapsedSections.toggle('pit-stops')}>
					<span class="chevron" class:rotated={collapsed['pit-stops']}>&#9660;</span>
				</button>
				<div class="section-body" class:collapsed={collapsed['pit-stops']}>
					<div class="grid-row grid-row--full">
						<PitStopStats data={pitstops} />
					</div>
				</div>
			</div>

			<!-- Row 3: Energy Bars + Delta Matrix -->
			<div id="section-energy" class="dashboard-section">
				<button class="section-toggle" onclick={() => collapsedSections.toggle('energy')}>
					<span class="chevron" class:rotated={collapsed['energy']}>&#9660;</span>
				</button>
				<div class="section-body" class:collapsed={collapsed['energy']}>
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
				</div>
			</div>

			<!-- Row 4: Energy Timeline (full width, per-driver) -->
			<div id="section-energy-timeline" class="dashboard-section">
				<button class="section-toggle" onclick={() => collapsedSections.toggle('energy-timeline')}>
					<span class="chevron" class:rotated={collapsed['energy-timeline']}>&#9660;</span>
				</button>
				<div class="section-body" class:collapsed={collapsed['energy-timeline']}>
					<div class="grid-row grid-row--full">
						<EnergyTimeline
							{raceId}
							drivers={driverList}
							defaultDriver={raceInfo.winner}
						/>
					</div>
				</div>
			</div>

			<!-- Row 5: Speed Trace (full width) -->
			<div id="section-speed-trace" class="dashboard-section">
				<button class="section-toggle" onclick={() => collapsedSections.toggle('speed-trace')}>
					<span class="chevron" class:rotated={collapsed['speed-trace']}>&#9660;</span>
				</button>
				<div class="section-body" class:collapsed={collapsed['speed-trace']}>
					<div class="grid-row grid-row--full">
						<SpeedTrace
							{raceId}
							drivers={driverList}
							circuit={circuitData}
							totalLaps={raceInfo?.total_laps || 58}
						/>
					</div>
				</div>
			</div>

			<!-- Row 6: Track Map + Traffic Analysis -->
			<div id="section-track-map" class="dashboard-section">
				<button class="section-toggle" onclick={() => collapsedSections.toggle('track-map')}>
					<span class="chevron" class:rotated={collapsed['track-map']}>&#9660;</span>
				</button>
				<div class="section-body" class:collapsed={collapsed['track-map']}>
					<div class="grid-row grid-row--full">
						<TrackMap
							{raceId}
							drivers={driverList}
							circuit={circuitData}
							totalLaps={raceInfo?.total_laps || 58}
						/>
					</div>
				</div>
			</div>

			<!-- Row 7: Traffic Analysis -->
			<div id="section-traffic" class="dashboard-section">
				<button class="section-toggle" onclick={() => collapsedSections.toggle('traffic')}>
					<span class="chevron" class:rotated={collapsed['traffic']}>&#9660;</span>
				</button>
				<div class="section-body" class:collapsed={collapsed['traffic']}>
					<div class="grid-row grid-row--full">
						<TrafficAnalysis {trafficData} loading={trafficLoading} />
					</div>
				</div>
			</div>
		</div>

	
	{:else}
		<!-- Qualifying Session -->
		{#if qualifyingLoading}
			<div class="quali-loading">
				<span>{$t('common.loading')}</span>
			</div>
		{:else if qualifyingError}
			<div class="quali-error">
				<span>{$t('common.no_data')}</span>
			</div>
		{:else if qualifyingData}
			<!-- Qualifying Insights -->
			{#if $showAnnotations}
				<RaceInsightsPanel
					annotations={annotations.annotations || []}
					chartTypes={['qualifying']}
				/>
			{/if}
			<div class="dashboard__grid">
				<!-- Qualifying Results Table -->
				<div id="section-qualifying-results" class="dashboard-section">
					<button class="section-toggle" onclick={() => collapsedSections.toggle('qualifying-results')}>
						<span class="chevron" class:rotated={collapsed['qualifying-results']}>&#9660;</span>
					</button>
					<div class="section-body" class:collapsed={collapsed['qualifying-results']}>
						<QualifyingResults drivers={qualifyingData.drivers || []} {raceId} />
					</div>
				</div>

				<!-- Sector Comparison -->
				<div id="section-sector-comparison" class="dashboard-section">
					<button class="section-toggle" onclick={() => collapsedSections.toggle('sector-comparison')}>
						<span class="chevron" class:rotated={collapsed['sector-comparison']}>&#9660;</span>
					</button>
					<div class="section-body" class:collapsed={collapsed['sector-comparison']}>
						<SectorComparison drivers={qualifyingData.drivers || []} />
					</div>
				</div>

				<!-- Ideal Laps -->
				<div id="section-ideal-laps" class="dashboard-section">
					<button class="section-toggle" onclick={() => collapsedSections.toggle('ideal-laps')}>
						<span class="chevron" class:rotated={collapsed['ideal-laps']}>&#9660;</span>
					</button>
					<div class="section-body" class:collapsed={collapsed['ideal-laps']}>
						<IdealLaps drivers={qualifyingData.drivers || []} />
					</div>
				</div>

				<!-- Qualifying Delta -->
				<div id="section-qualifying-delta" class="dashboard-section">
					<button class="section-toggle" onclick={() => collapsedSections.toggle('qualifying-delta')}>
						<span class="chevron" class:rotated={collapsed['qualifying-delta']}>&#9660;</span>
					</button>
					<div class="section-body" class:collapsed={collapsed['qualifying-delta']}>
						<QualifyingDelta drivers={qualifyingData.drivers || []} />
					</div>
				</div>
			</div>
		{/if}
	{/if}
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
		font-size: 26px;
		font-weight: 700;
		letter-spacing: -0.02em;
		margin-bottom: var(--space-xs);
	}
	.dashboard__meta {
		display: flex;
		align-items: center;
		gap: var(--space-xs);
		font-size: var(--font-size-label);
		color: var(--text-secondary);
	}
	.sep {
		color: var(--text-muted);
	}
	.winner {
		color: var(--accent);
		font-weight: 500;
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

	/* Collapsible sections */
	.dashboard-section {
		position: relative;
		min-height: 28px;
	}
	.section-toggle {
		position: absolute;
		top: 4px;
		right: 4px;
		z-index: 5;
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		cursor: pointer;
		padding: 4px 6px;
		line-height: 1;
		opacity: 0.6;
		transition: opacity 0.15s;
	}
	.section-toggle:hover {
		opacity: 1;
	}
	.chevron {
		display: inline-block;
		font-size: 10px;
		color: var(--text-muted);
		transition: transform 0.2s ease;
	}
	.chevron.rotated {
		transform: rotate(-90deg);
	}
	.section-toggle:hover .chevron {
		color: var(--text-secondary);
	}
	.section-body {
		max-height: 2000px;
		opacity: 1;
		overflow: visible;
		transition: max-height 0.35s ease, opacity 0.25s ease;
	}
	.section-body.collapsed {
		max-height: 0;
		opacity: 0;
		overflow: hidden;
	}

	/* Toolbar: filter + action buttons */
	.dashboard__toolbar {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-md);
		margin-bottom: var(--space-lg);
	}
	.dashboard__filter {
		flex: 1;
	}
	.dashboard__actions {
		display: flex;
		gap: var(--space-sm);
		flex-shrink: 0;
		padding-top: 2px;
	}
	.dashboard__action-btn {
		font-family: var(--font-mono);
		font-size: var(--font-size-small);
		color: var(--text-secondary);
		padding: 6px 12px;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		text-decoration: none;
		transition: all 0.15s;
		white-space: nowrap;
	}
	.dashboard__action-btn:hover {
		color: var(--text-primary);
		border-color: var(--text-muted);
		text-decoration: none;
	}
	.dashboard__action-btn.active {
		background: var(--bg-secondary);
		color: var(--text-primary);
		border-color: var(--text-muted);
	}
	.dashboard__action-btn--broadcast:hover {
		background: var(--accent);
		color: var(--bg-primary);
		border-color: var(--accent);
	}

	/* Qualifying loading/error states */
	.quali-loading,
	.quali-error {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-xl);
		font-family: var(--font-mono);
		font-size: 14px;
		color: var(--text-muted);
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
			font-size: 16px;
		}
		.dashboard__meta {
			flex-wrap: wrap;
		}
		.dashboard__toolbar {
			flex-direction: column;
			align-items: stretch;
		}
		.dashboard__actions {
			justify-content: flex-start;
			flex-wrap: wrap;
		}
		.dashboard__action-btn {
			min-height: 44px;
			display: flex;
			align-items: center;
		}
	}

	@media (max-width: 480px) {
		.dashboard__title {
			font-size: 15px;
		}
		.dashboard__meta {
			font-size: var(--font-size-small);
		}
	}
</style>
