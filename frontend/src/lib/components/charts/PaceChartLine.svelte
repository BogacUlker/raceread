<!--
	SVG line layer for PaceChart.
	Renders one path per selected driver, colored by team.
	Supports hover highlighting, multi-pin (up to 5) via shared stores, and pit stop markers.
-->
<script>
	import { getContext } from 'svelte';
	import { TEAM_COLORS, COMPOUND_COLORS } from '$lib/constants.js';
	import { hoveredDriver, pinnedDriver } from '$lib/stores/race.js';
	import { t } from '$lib/i18n/index.js';

	const { xScale, yScale, width, height, padding } = getContext('LayerCake');

	let { driverData, yKey, pitMarkers = [] } = $props();

	const clipId = 'pace-clip-' + Math.random().toString(36).slice(2, 8);

	let hovered = $state(null);
	let pinned = $state([]);
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
		if (pinned.length > 0) return pinned.includes(driver) ? 1 : 0.12;
		if (hovered) return driver === hovered ? 1 : 0.2;
		return 0.85;
	}

	function getStrokeWidth(driver) {
		if (pinned.length > 0) return pinned.includes(driver) ? 2.8 : 1.2;
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
		pinnedDriver.update(arr => {
			if (arr.includes(driver)) {
				return arr.filter(d => d !== driver);
			}
			if (arr.length >= 5) return arr; // max 5
			return [...arr, driver];
		});
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<g class="pace-lines" onmouseleave={handleLeave}>
	<defs>
		<clipPath id={clipId}>
			<rect x="0" y="0" width={$width} height={$height} />
		</clipPath>
	</defs>
	<g clip-path="url(#{clipId})">
	{#each driverData as { driver, team, laps }}
		{@const color = TEAM_COLORS[team] || '#888'}
		{@const d = buildPath(laps)}
		{#if d}
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

	</g>

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