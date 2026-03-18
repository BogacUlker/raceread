<!--
	Energy Timeline - lap-by-lap stacked area chart per driver.
	Uses LayerCake with custom stacked area SVG layer.
	Single-driver selector synced with selectedEnergyDriver store.
-->
<script>
	import { LayerCake, Svg, Html } from 'layercake';
	import { scaleLinear } from 'd3-scale';
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS, ENERGY_COLORS } from '$lib/constants.js';
	import InferredBadge from '$lib/components/ui/InferredBadge.svelte';
	import EnergyTimelineLayers from './EnergyTimelineLayers.svelte';
	import EnergyTimelineTooltip from './EnergyTimelineTooltip.svelte';
	import LoadingSpinner from '$lib/components/ui/LoadingSpinner.svelte';
	import { get } from 'svelte/store';
	import { api } from '$lib/api.js';
	import { selectedEnergyDriver } from '$lib/stores/race.js';

	/**
	 * @type {{
	 *   raceId: string,
	 *   drivers: Array<{driver: string, team: string}>,
	 *   defaultDriver: string
	 * }}
	 */
	let { raceId, drivers, defaultDriver, compareDriver = '' } = $props();

	let selectedDriver = $state('');
	let energyData = $state(null);
	let loading = $state(false);
	let cache = new Map();

	// Initialize selectedDriver from store or default
	$effect(() => {
		if (!selectedDriver && defaultDriver) {
			selectedDriver = defaultDriver;
			selectedEnergyDriver.set(defaultDriver);
		}
	});

	// Sync from store (when EnergyBars selects a driver)
	$effect(() => {
		const v = get(selectedEnergyDriver);
		if (v && v !== selectedDriver) {
			selectedDriver = v;
		}
	});

	// Sync from parent compare page when top-level selection changes
	$effect(() => {
		if (compareDriver && compareDriver !== selectedDriver) {
			selectedDriver = compareDriver;
			selectedEnergyDriver.set(compareDriver);
		}
	});

	// Sync store when local dropdown changes
	function handleDriverChange(e) {
		const driver = e.target.value;
		selectedDriver = driver;
		selectedEnergyDriver.set(driver);
	}

	async function loadDriverEnergy(driver) {
		if (cache.has(driver)) {
			energyData = cache.get(driver);
			return;
		}
		loading = true;
		try {
			const data = await api(`/api/races/${raceId}/energy?driver=${driver}`);
			cache.set(driver, data);
			energyData = data;
		} catch (e) {
			console.error('Failed to load energy data:', e);
			energyData = null;
		}
		loading = false;
	}

	$effect(() => {
		if (selectedDriver) {
			loadDriverEnergy(selectedDriver);
		}
	});

	let laps = $derived(energyData?.laps ?? []);
	let xDomain = $derived(
		laps.length ? [laps[0].lap, laps[laps.length - 1].lap] : [1, 58]
	);
</script>

<div class="chart-card">
	<div class="chart-card__header">
		<span class="chart-card__title">{$t('charts.energy_timeline')}</span>
		<InferredBadge />
		<div class="driver-select">
			<select value={selectedDriver} onchange={handleDriverChange}>
				{#each drivers as d}
					<option value={d.driver}>{d.driver}</option>
				{/each}
			</select>
		</div>
	</div>

	<!-- Legend -->
	<div class="legend">
		<span class="legend__item">
			<span class="legend__dot" style="background: {ENERGY_COLORS.deploy}"></span>
			{$t('charts.deploy')}
		</span>
		<span class="legend__item">
			<span class="legend__dot" style="background: {ENERGY_COLORS.harvest}"></span>
			{$t('charts.harvest')}
		</span>
		<span class="legend__item">
			<span class="legend__dot" style="background: {ENERGY_COLORS.clip}"></span>
			{$t('charts.clip')}
		</span>
	</div>

	<div class="chart-container chart-interactive">
		{#if loading}
			<LoadingSpinner />
		{:else if laps.length > 0}
			<LayerCake
				data={laps}
				x="lap"
				xScale={scaleLinear()}
				yScale={scaleLinear()}
				xDomain={xDomain}
				yDomain={[0, 100]}
				padding={{ top: 8, right: 16, bottom: 32, left: 40 }}
			>
				<Svg>
					<EnergyTimelineLayers />
				</Svg>
				<Html>
					<EnergyTimelineTooltip />
				</Html>
			</LayerCake>
		{:else}
			<div class="no-data">{$t('common.no_data')}</div>
		{/if}
	</div>
</div>

<style>
	.chart-container {
		width: 100%;
		height: 250px;
		position: relative;
	}
	.driver-select {
		margin-left: auto;
	}
	.driver-select select {
		font-family: var(--font-mono);
		font-size: 13px;
		padding: 3px 8px;
		background: var(--bg-primary);
		color: var(--text-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		cursor: pointer;
	}
	.legend {
		display: flex;
		gap: var(--space-md);
		margin-bottom: var(--space-sm);
	}
	.legend__item {
		display: flex;
		align-items: center;
		gap: 4px;
		font-family: var(--font-mono);
		font-size: 12px;
		color: var(--text-secondary);
	}
	.legend__dot {
		width: 8px;
		height: 8px;
		border-radius: 2px;
	}
	.no-data {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		color: var(--text-muted);
		font-family: var(--font-mono);
		font-size: 13px;
	}

	@media (max-width: 768px) {
		.chart-container {
			height: 200px;
		}
		.driver-select select {
			min-height: 40px;
		}
	}

	@media (max-width: 480px) {
		.chart-container {
			height: 180px;
		}
	}
</style>
