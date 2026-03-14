<!--
	Race Pace Chart - main LayerCake multi-line chart.
	Gap-to-leader (default) with raw time toggle.
	SC/VSC overlays, hover tooltips, pit stop markers.
	Interactive legend with multi-pin (up to 5 drivers).
-->
<script>
	import { LayerCake, Svg, Html } from 'layercake';
	import { scaleLinear } from 'd3-scale';
	import { extent, max } from 'd3-array';
	import { t } from '$lib/i18n/index.js';
	import { computeGapToLeader } from '$lib/utils/format.js';
	import { TEAM_COLORS } from '$lib/constants.js';
	import { hoveredDriver, pinnedDriver } from '$lib/stores/race.js';

	import PaceChartLine from './PaceChartLine.svelte';
	import PaceChartAxis from './PaceChartAxis.svelte';
	import PaceChartOverlay from './PaceChartOverlay.svelte';
	import PaceChartTooltip from './PaceChartTooltip.svelte';
	import PaceChartAnnotations from './PaceChartAnnotations.svelte';

	let { laps, selectedDrivers, vscLaps = [], annotations = [], strategy } = $props();

	let viewMode = $state('gap');

	let hovered = $state(null);
	let pinned = $state([]);
	const unsubH = hoveredDriver.subscribe(v => { hovered = v; });
	const unsubP = pinnedDriver.subscribe(v => { pinned = v; });

	let lapsWithGap = $derived(computeGapToLeader(laps));

	let filteredData = $derived(
		lapsWithGap.filter((d) => selectedDrivers.includes(d.driver))
	);

	let yKey = $derived(viewMode === 'gap' ? 'gap' : 'time_s');

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
				const sorted = [...allVals].sort((a, b) => a - b);
				const p95 = sorted[Math.floor(sorted.length * 0.95)];
				return [0, Math.max(p95 * 1.15, 1)];
			}
			const [lo, hi] = extent(allVals);
			const pad = (hi - lo) * 0.05;
			return [hi + pad, lo - pad];
		})()
	);

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

	// Legend: sort by median pace (fastest first)
	let legendDrivers = $derived(
		filteredData
			.map(d => {
				const times = d.laps.filter(l => l.gap != null).map(l => l.gap);
				const median = times.length ? times.sort((a, b) => a - b)[Math.floor(times.length / 2)] : 999;
				return { driver: d.driver, team: d.team, median };
			})
			.sort((a, b) => a.median - b.median)
	);

	function legendEnter(driver) {
		hoveredDriver.set(driver);
	}
	function legendLeave() {
		hoveredDriver.set(null);
	}
	function legendClick(driver) {
		pinnedDriver.update(arr => {
			if (arr.includes(driver)) {
				return arr.filter(d => d !== driver);
			}
			if (arr.length >= 5) return arr; // max 5
			return [...arr, driver];
		});
	}
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

	<div class="pace-wrapper">
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

		<!-- Interactive driver legend (multi-select up to 5) -->
		{#if filteredData.length > 0}
			<div class="pace-legend">
				<div class="pace-legend__hint">
					{pinned.length > 0 ? `${pinned.length}/5` : ''}
				</div>
				{#each legendDrivers as { driver, team }}
					{@const color = TEAM_COLORS[team] || '#888'}
					{@const isActive = pinned.includes(driver)}
					{@const isDimmed = pinned.length > 0 && !pinned.includes(driver)}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<div
						class="pace-legend__item"
						class:active={isActive}
						class:dimmed={isDimmed}
						class:hovered={hovered === driver && pinned.length === 0}
						class:at-limit={pinned.length >= 5 && !isActive}
						onmouseenter={() => legendEnter(driver)}
						onmouseleave={legendLeave}
						onclick={() => legendClick(driver)}
					>
						<span class="pace-legend__dot" style="background: {color}"></span>
						<span class="pace-legend__name">{driver}</span>
					</div>
				{/each}
				{#if pinned.length > 0}
					<button class="pace-legend__clear" onclick={() => pinnedDriver.set([])}>
						Clear
					</button>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	.pace-wrapper {
		display: flex;
		gap: 8px;
	}
	.chart-container {
		width: 100%;
		height: 420px;
		position: relative;
		flex: 1;
		min-width: 0;
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

	/* Interactive legend */
	.pace-legend {
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: 4px 0;
		min-width: 72px;
		max-height: 420px;
		overflow-y: auto;
	}
	.pace-legend__hint {
		font-family: var(--font-mono);
		font-size: 9px;
		color: var(--text-muted);
		text-align: center;
		min-height: 14px;
	}
	.pace-legend__item {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 3px 8px;
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: all 0.12s;
		opacity: 0.7;
	}
	.pace-legend__item:hover,
	.pace-legend__item.hovered {
		opacity: 1;
		background: var(--bg-secondary);
	}
	.pace-legend__item.active {
		opacity: 1;
		background: var(--bg-secondary);
		border-left: 2px solid var(--text-primary);
		padding-left: 6px;
	}
	.pace-legend__item.dimmed {
		opacity: 0.3;
	}
	.pace-legend__item.at-limit {
		cursor: not-allowed;
		opacity: 0.2;
	}
	.pace-legend__dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.pace-legend__name {
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 500;
		color: var(--text-primary);
		white-space: nowrap;
	}
	.pace-legend__clear {
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--text-muted);
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 2px 6px;
		cursor: pointer;
		margin-top: 4px;
		align-self: center;
	}
	.pace-legend__clear:hover {
		color: var(--text-primary);
		border-color: var(--text-muted);
	}
</style>