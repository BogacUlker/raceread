<!--
	Race Pace Chart - main LayerCake multi-line chart.
	Gap-to-leader (default) with raw time toggle.
	SC/VSC overlays, hover tooltips, pit stop markers.
-->
<script>
	import { LayerCake, Svg, Html } from 'layercake';
	import { scaleLinear } from 'd3-scale';
	import { extent, max } from 'd3-array';
	import { t } from '$lib/i18n/index.js';
	import { computeGapToLeader } from '$lib/utils/format.js';

	import PaceChartLine from './PaceChartLine.svelte';
	import PaceChartAxis from './PaceChartAxis.svelte';
	import PaceChartOverlay from './PaceChartOverlay.svelte';
	import PaceChartTooltip from './PaceChartTooltip.svelte';
	import PaceChartAnnotations from './PaceChartAnnotations.svelte';

	/**
	 * @type {{
	 *   laps: Array<{driver: string, team: string, laps: Array}>,
	 *   selectedDrivers: string[],
	 *   vscLaps: number[],
	 *   annotations: Array,
	 *   strategy: {drivers: Array} | undefined
	 * }}
	 */
	let { laps, selectedDrivers, vscLaps = [], annotations = [], strategy } = $props();

	let viewMode = $state('gap');

	// Add gap computations to all drivers
	let lapsWithGap = $derived(computeGapToLeader(laps));

	// Filter to selected drivers only
	let filteredData = $derived(
		lapsWithGap.filter((d) => selectedDrivers.includes(d.driver))
	);

	let yKey = $derived(viewMode === 'gap' ? 'gap' : 'time_s');

	// Compute domains
	let xDomain = $derived(
		(() => {
			const allLapNums = filteredData.flatMap((d) => d.laps.map((l) => l.lap));
			if (!allLapNums.length) return [1, 58];
			return extent(allLapNums);
		})()
	);

	let yDomain = $derived(
		(() => {
			const allVals = filteredData.flatMap((d) =>
				d.laps.filter((l) => l[yKey] != null).map((l) => l[yKey])
			);
			if (!allVals.length) return [0, 5];
			if (viewMode === 'gap') {
				return [0, Math.max(max(allVals) * 1.1, 1)];
			}
			// Raw mode: inverted (lower time = higher on chart)
			const [lo, hi] = extent(allVals);
			const pad = (hi - lo) * 0.05;
			return [hi + pad, lo - pad];
		})()
	);

	// Pit stop markers: for each selected driver, find pit laps and the compound they switched to
	let pitMarkers = $derived(
		(() => {
			if (!strategy?.drivers) return [];
			const markers = [];
			for (const sd of strategy.drivers) {
				if (!selectedDrivers.includes(sd.driver)) continue;
				const driverLaps = filteredData.find((d) => d.driver === sd.driver);
				if (!driverLaps) continue;
				for (const pitLap of sd.pit_laps || []) {
					const nextStint = sd.stints.find((s) => s.start_lap === pitLap + 1);
					const prevStint = sd.stints.find((s) => s.end_lap === pitLap);
					const lapData = driverLaps.laps.find((l) => l.lap === pitLap);
					if (!lapData || lapData[yKey] == null) continue;
					markers.push({
						driver: sd.driver,
						team: sd.team,
						lap: pitLap,
						yVal: lapData[yKey],
						newCompound: nextStint?.compound,
						oldCompound: prevStint?.compound
					});
				}
			}
			return markers;
		})()
	);
</script>

<div class="chart-card">
	<div class="chart-card__header">
		<span class="chart-card__title">{$t('charts.pace')}</span>
		<div class="view-toggle">
			<button
				class="toggle-btn"
				class:active={viewMode === 'gap'}
				onclick={() => (viewMode = 'gap')}
			>
				{$t('charts.gap_mode')}
			</button>
			<button
				class="toggle-btn"
				class:active={viewMode === 'raw'}
				onclick={() => (viewMode = 'raw')}
			>
				{$t('charts.raw_mode')}
			</button>
		</div>
	</div>

	<div class="chart-container chart-interactive">
		{#if filteredData.length > 0}
			<LayerCake
				data={filteredData}
				x="lap"
				y={yKey}
				xScale={scaleLinear()}
				yScale={scaleLinear()}
				xDomain={xDomain}
				yDomain={yDomain}
				padding={{ top: 16, right: 16, bottom: 40, left: 56 }}
			>
				<Svg>
					<PaceChartOverlay {vscLaps} />
					<PaceChartLine driverData={filteredData} {yKey} {pitMarkers} />
					<PaceChartAnnotations {annotations} driverData={filteredData} {yKey} />
					<PaceChartAxis {viewMode} />
				</Svg>
				<Html>
					<PaceChartTooltip driverData={filteredData} {viewMode} {annotations} {vscLaps} />
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
		height: 350px;
		position: relative;
	}
	.view-toggle {
		display: flex;
		gap: 2px;
		background: var(--bg-primary);
		border-radius: var(--radius-sm);
		padding: 2px;
	}
	.toggle-btn {
		font-family: var(--font-mono);
		font-size: 13px;
		padding: 3px 10px;
		border: none;
		border-radius: 3px;
		background: transparent;
		color: var(--text-muted);
		cursor: pointer;
		transition: all 0.15s;
	}
	.toggle-btn.active {
		background: var(--bg-card);
		color: var(--text-primary);
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
</style>
