<!--
	SVG line layer for PaceChart.
	Renders one path per selected driver, colored by team.
	Supports hover highlighting, pinning via shared stores, and pit stop markers.
-->
<script>
	import { getContext } from 'svelte';
	import { TEAM_COLORS, COMPOUND_COLORS } from '$lib/constants.js';
	import { hoveredDriver, pinnedDriver } from '$lib/stores/race.js';
	import { t } from '$lib/i18n/index.js';

	const { xScale, yScale } = getContext('LayerCake');

	/**
	 * @type {{
	 *   driverData: Array<{driver: string, team: string, laps: Array}>,
	 *   yKey: string,
	 *   pitMarkers: Array<{driver: string, team: string, lap: number, yVal: number, newCompound: string, oldCompound: string}> | undefined
	 * }}
	 */
	let { driverData, yKey, pitMarkers = [] } = $props();

	let hovered = $state(null);
	let pinned = $state(null);
	let hoveredPit = $state(null);
	let pitTooltipX = $state(0);
	let pitTooltipY = $state(0);

	const unsubHover = hoveredDriver.subscribe((v) => { hovered = v; });
	const unsubPin = pinnedDriver.subscribe((v) => { pinned = v; });

	function buildPath(laps) {
		const points = laps
			.filter((d) => d[yKey] != null)
			.map((d) => `${$xScale(d.lap)},${$yScale(d[yKey])}`);
		return points.length > 1 ? 'M' + points.join('L') : '';
	}

	function getOpacity(driver) {
		if (pinned) return driver === pinned ? 1 : 0.15;
		if (hovered) return driver === hovered ? 1 : 0.2;
		return 0.85;
	}

	function getStrokeWidth(driver) {
		if (pinned) return driver === pinned ? 3 : 1.5;
		if (hovered) return driver === hovered ? 3 : 1.5;
		return 1.8;
	}

	function handleEnter(driver) {
		hoveredDriver.set(driver);
	}

	function handleLeave() {
		hoveredDriver.set(null);
	}

	function handleClick(driver) {
		if (pinned === driver) {
			pinnedDriver.set(null);
		} else {
			pinnedDriver.set(driver);
		}
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<g class="pace-lines" onmouseleave={handleLeave}>
	{#each driverData as { driver, team, laps }}
		{@const color = TEAM_COLORS[team] || '#888'}
		{@const d = buildPath(laps)}
		{#if d}
			<!-- Visible path -->
			<path
				class="pace-line"
				{d}
				stroke={color}
				fill="none"
				stroke-width={getStrokeWidth(driver)}
				stroke-linejoin="round"
				stroke-linecap="round"
				opacity={getOpacity(driver)}
				style="transition: opacity 0.15s, stroke-width 0.15s;"
			/>
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- Invisible hit area for easier hover targeting -->
			<path
				{d}
				stroke="transparent"
				fill="none"
				stroke-width="14"
				style="cursor: pointer;"
				onmouseenter={() => handleEnter(driver)}
				onclick={() => handleClick(driver)}
			/>
		{/if}
	{/each}

	<!-- Pit stop markers -->
	{#each pitMarkers as pm}
		{@const cx = $xScale(pm.lap)}
		{@const cy = $yScale(pm.yVal)}
		{@const newColor = pm.newCompound ? COMPOUND_COLORS[pm.newCompound] || '#888' : '#888'}
		<circle
			{cx}
			{cy}
			r="4"
			fill={newColor}
			stroke="var(--bg-card)"
			stroke-width="1.5"
			style="cursor: pointer;"
			onmouseenter={(e) => {
				hoveredPit = pm;
				const svg = e.currentTarget.closest('svg');
				const rect = svg.getBoundingClientRect();
				pitTooltipX = e.clientX - rect.left;
				pitTooltipY = e.clientY - rect.top;
			}}
			onmouseleave={() => { hoveredPit = null; }}
		/>
	{/each}

	<!-- Pit tooltip -->
	{#if hoveredPit}
		<foreignObject
			x={pitTooltipX + 10}
			y={pitTooltipY - 32}
			width="180"
			height="28"
			style="pointer-events: none; overflow: visible;"
		>
			<div class="pit-tooltip">
				{$t('tooltip.pit_stop')} {$t('tooltip.lap')} {hoveredPit.lap}: {hoveredPit.oldCompound || '?'} &rarr; {hoveredPit.newCompound || '?'}
			</div>
		</foreignObject>
	{/if}
</g>

<style>
	:global(.pit-tooltip) {
		font-family: var(--font-mono);
		font-size: 12px;
		color: var(--text-primary);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		padding: 4px 8px;
		border-radius: 4px;
		white-space: nowrap;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
	}
</style>
