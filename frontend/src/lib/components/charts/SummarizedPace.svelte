<!--
	Summarized Pace - horizontal bar+dot chart showing median pace per driver.
	Sorted by median time (fastest first).
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS } from '$lib/constants.js';
	import { get } from 'svelte/store';
	import { hoveredDriver, pinnedDriver } from '$lib/stores/race.js';
	import { median } from 'd3-array';
	import { scaleLinear } from 'd3-scale';

	/**
	 * @type {{ laps: Array<{driver: string, team: string, laps: Array}> }}
	 */
	let { laps } = $props();

	let hovered = $state(null);
	let pinned = $state([]);
	$effect(() => { const unsub = hoveredDriver.subscribe(v => hovered = v); return unsub; });
	$effect(() => { const unsub = pinnedDriver.subscribe(v => pinned = v); return unsub; });

	// Compute median lap time per driver (excluding inaccurate/null laps)
	let driverMedians = $derived(
		laps
			.map(({ driver, team, laps: driverLaps }) => {
				const validTimes = driverLaps
					.filter((l) => l.time_s != null && l.is_accurate !== false && l.lap > 1)
					.map((l) => l.time_s);
				const med = median(validTimes);
				return { driver, team, median: med ?? 0, count: validTimes.length };
			})
			.filter((d) => d.count > 0)
			.sort((a, b) => a.median - b.median)
	);

	let fastest = $derived(driverMedians[0]?.median ?? 0);
	let slowest = $derived(driverMedians[driverMedians.length - 1]?.median ?? fastest + 3);

	let barScale = $derived(
		scaleLinear()
			.domain([fastest, slowest])
			.range([100, 20])
	);
</script>

<div class="chart-card">
	<div class="chart-card__header">
		<span class="chart-card__title">{$t('charts.summarized_pace')}</span>
	</div>

	<div class="summarized">
		{#each driverMedians as d}
			{@const color = TEAM_COLORS[d.team] || '#888'}
			{@const delta = d.median - fastest}
			{@const isHighlighted = hovered === d.driver || (pinned.length > 0 && pinned.includes(d.driver))}
			{@const isDimmed = (hovered != null && hovered !== d.driver && pinned.length === 0) || (pinned.length > 0 && !pinned.includes(d.driver))}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				class="row"
				class:highlighted={isHighlighted}
				class:dimmed={isDimmed}
				onmouseenter={() => hoveredDriver.set(d.driver)}
				onmouseleave={() => hoveredDriver.set(null)}
			>
				<span class="row__driver" style="color: {color}">{d.driver}</span>
				<div class="row__bar-wrap">
					<div class="row__bar" style="width: {barScale(d.median)}%; background: {color}">
					</div>
				</div>
				<span class="row__time">{d.median.toFixed(2)}s</span>
				<span class="row__delta">
					{delta === 0 ? '' : `+${delta.toFixed(2)}`}
				</span>
			</div>
		{/each}
	</div>
</div>

<style>
	.summarized {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.row {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 2px 4px;
		border-radius: 3px;
		cursor: pointer;
		transition: opacity 0.15s, background 0.15s;
	}
	.row:hover,
	.row.highlighted {
		background: var(--bg-secondary);
	}
	.row.dimmed {
		opacity: 0.3;
	}
	.row__driver {
		font-family: var(--font-mono);
		font-size: var(--font-size-label);
		font-weight: 600;
		width: 38px;
		flex-shrink: 0;
	}
	.row__bar-wrap {
		flex: 1;
		height: 18px;
		background: var(--bg-primary);
		border-radius: 3px;
		overflow: hidden;
	}
	.row__bar {
		height: 100%;
		border-radius: 3px;
		opacity: 0.7;
		transition: width 0.3s ease, opacity 0.15s;
	}
	.row.highlighted .row__bar,
	.row:hover .row__bar {
		opacity: 1;
	}
	.row__time {
		font-family: var(--font-mono);
		font-size: var(--font-size-label);
		color: var(--text-secondary);
		width: 58px;
		text-align: right;
		flex-shrink: 0;
	}
	.row__delta {
		font-family: var(--font-mono);
		font-size: var(--font-size-compact);
		color: var(--text-muted);
		width: 50px;
		text-align: right;
		flex-shrink: 0;
	}
</style>
