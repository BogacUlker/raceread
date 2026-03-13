<!--
	Strategy Timeline - horizontal bar chart showing tire stints per driver.
	SVG-based with compound colors, pit stop markers, and cross-chart sync line.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS, COMPOUND_COLORS } from '$lib/constants.js';
	import { scaleLinear } from 'd3-scale';
	import { hoveredLap as hoveredLapStore } from '$lib/stores/race.js';

	/**
	 * @type {{
	 *   drivers: Array<{driver: string, team: string, stints: Array, pit_laps: number[]}>,
	 *   totalLaps: number,
	 *   vscLaps: number[]
	 * }}
	 */
	let { drivers, totalLaps, vscLaps = [] } = $props();

	const rowHeight = 28;
	const rowGap = 4;
	const padding = { top: 24, right: 16, bottom: 32, left: 50 };

	let svgHeight = $derived(padding.top + drivers.length * (rowHeight + rowGap) + padding.bottom);
	let svgWidth = $state(800);

	let xScale = $derived(
		scaleLinear()
			.domain([0, totalLaps])
			.range([padding.left, svgWidth - padding.right])
	);

	let xTicks = $derived(
		(() => {
			const step = totalLaps > 40 ? 10 : 5;
			const ticks = [];
			for (let i = 0; i <= totalLaps; i += step) ticks.push(i);
			if (ticks[ticks.length - 1] !== totalLaps) ticks.push(totalLaps);
			return ticks;
		})()
	);

	// VSC ranges
	let vscRanges = $derived(
		(() => {
			if (!vscLaps.length) return [];
			const sorted = [...vscLaps].sort((a, b) => a - b);
			const result = [];
			let start = sorted[0];
			let end = sorted[0];
			for (let i = 1; i < sorted.length; i++) {
				if (sorted[i] === end + 1) {
					end = sorted[i];
				} else {
					result.push({ start, end });
					start = sorted[i];
					end = sorted[i];
				}
			}
			result.push({ start, end });
			return result;
		})()
	);

	// Cross-chart sync
	let syncLap = $state(null);
	const unsubLap = hoveredLapStore.subscribe((v) => { syncLap = v; });

	// Local tooltip state
	let tooltip = $state(null);
	let tooltipX = $state(0);
	let tooltipY = $state(0);

	function handleSvgMouseMove(e) {
		const svg = e.currentTarget;
		const rect = svg.getBoundingClientRect();
		const x = e.clientX - rect.left;
		const y = e.clientY - rect.top;

		// Only track lap from svg background (not from stint rects)
		if (e.target === svg || e.target.classList.contains('strategy-bg')) {
			const lap = Math.round(xScale.invert(x));
			if (lap >= 0 && lap <= totalLaps) {
				hoveredLapStore.set(lap);
			}
		}

		tooltipX = x;
		tooltipY = y;
	}

	function handleSvgMouseLeave() {
		hoveredLapStore.set(null);
		tooltip = null;
	}

	function handleStintEnter(driver, stint, e) {
		tooltip = {
			type: 'stint',
			driver,
			compound: stint.compound,
			startLap: stint.start_lap,
			endLap: stint.end_lap,
			laps: stint.laps
		};
		updateTooltipFromEvent(e);
	}

	function handlePitEnter(driver, pitLap, e) {
		tooltip = {
			type: 'pit',
			driver,
			lap: pitLap
		};
		updateTooltipFromEvent(e);
	}

	function handleElementMove(e) {
		updateTooltipFromEvent(e);
		// Also update hoveredLap for cross-chart sync
		const svg = e.currentTarget.closest('svg');
		if (!svg) return;
		const rect = svg.getBoundingClientRect();
		const x = e.clientX - rect.left;
		const lap = Math.round(xScale.invert(x));
		if (lap >= 0 && lap <= totalLaps) {
			hoveredLapStore.set(lap);
		}
	}

	function handleElementLeave() {
		tooltip = null;
	}

	function updateTooltipFromEvent(e) {
		const svg = e.currentTarget.closest('svg');
		if (!svg) return;
		const rect = svg.getBoundingClientRect();
		tooltipX = e.clientX - rect.left;
		tooltipY = e.clientY - rect.top;
	}
</script>

<div class="chart-card">
	<div class="chart-card__header">
		<span class="chart-card__title">{$t('charts.strategy')}</span>
	</div>

	<div class="strategy-wrap" bind:clientWidth={svgWidth}>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<svg
			width={svgWidth}
			height={svgHeight}
			style="cursor: crosshair;"
			onmousemove={handleSvgMouseMove}
			onmouseleave={handleSvgMouseLeave}
		>
			<!-- Background rect for mouse tracking -->
			<rect
				class="strategy-bg"
				x={padding.left}
				y={padding.top}
				width={svgWidth - padding.left - padding.right}
				height={svgHeight - padding.top - padding.bottom}
				fill="transparent"
			/>

			<!-- VSC shading -->
			{#each vscRanges as range}
				<rect
					x={xScale(range.start - 0.5)}
					y={padding.top}
					width={xScale(range.end + 0.5) - xScale(range.start - 0.5)}
					height={svgHeight - padding.top - padding.bottom}
					fill="#F59E0B"
					fill-opacity="0.06"
					style="pointer-events: none;"
				/>
			{/each}

			<!-- Driver rows -->
			{#each drivers as d, i}
				{@const y = padding.top + i * (rowHeight + rowGap)}
				{@const color = TEAM_COLORS[d.team] || '#888'}

				<!-- Driver label -->
				<text
					x={padding.left - 8}
					y={y + rowHeight / 2}
					text-anchor="end"
					dominant-baseline="middle"
					fill={color}
					font-family="var(--font-mono)"
					font-size="11"
					font-weight="600"
					style="pointer-events: none;"
				>
					{d.driver}
				</text>

				<!-- Stints -->
				{#each d.stints as stint}
					{@const sx = xScale(stint.start_lap - 1)}
					{@const sw = xScale(stint.end_lap) - sx}
					{@const compoundColor = COMPOUND_COLORS[stint.compound] || '#888'}
					<rect
						x={sx}
						y={y + 2}
						width={sw}
						height={rowHeight - 4}
						fill={compoundColor}
						rx="3"
						opacity="0.75"
						style="cursor: pointer;"
						onmouseenter={(e) => handleStintEnter(d.driver, stint, e)}
						onmousemove={handleElementMove}
						onmouseleave={handleElementLeave}
					/>
					<!-- Compound label inside bar -->
					{#if sw > 30}
						<text
							x={sx + sw / 2}
							y={y + rowHeight / 2}
							text-anchor="middle"
							dominant-baseline="middle"
							fill={stint.compound === 'HARD' ? '#333' : '#000'}
							font-family="var(--font-mono)"
							font-size="9"
							font-weight="600"
							style="pointer-events: none;"
						>
							{stint.compound.charAt(0)}
						</text>
					{/if}
				{/each}

				<!-- Pit stop markers -->
				{#each d.pit_laps as pitLap}
					<!-- Invisible wider hit area -->
					<line
						x1={xScale(pitLap)}
						y1={y}
						x2={xScale(pitLap)}
						y2={y + rowHeight}
						stroke="transparent"
						stroke-width="8"
						style="cursor: pointer;"
						onmouseenter={(e) => handlePitEnter(d.driver, pitLap, e)}
						onmousemove={handleElementMove}
						onmouseleave={handleElementLeave}
					/>
					<!-- Visible pit line -->
					<line
						x1={xScale(pitLap)}
						y1={y}
						x2={xScale(pitLap)}
						y2={y + rowHeight}
						stroke="var(--text-muted)"
						stroke-width="1"
						stroke-dasharray="2,2"
						style="pointer-events: none;"
					/>
				{/each}
			{/each}

			<!-- Cross-chart sync line -->
			{#if syncLap != null}
				<line
					x1={xScale(syncLap)}
					y1={padding.top}
					x2={xScale(syncLap)}
					y2={svgHeight - padding.bottom}
					stroke="var(--text-muted)"
					stroke-width="1"
					stroke-dasharray="4,3"
					opacity="0.5"
					style="pointer-events: none;"
				/>
			{/if}

			<!-- X axis -->
			{#each xTicks as tick}
				<g transform="translate({xScale(tick)}, {svgHeight - padding.bottom})">
					<line y1="0" y2="5" stroke="var(--border)" />
					<text
						y="16"
						text-anchor="middle"
						fill="var(--text-muted)"
						font-family="var(--font-mono)"
						font-size="10"
					>
						{tick}
					</text>
				</g>
			{/each}

			<!-- Tooltip via foreignObject -->
			{#if tooltip}
				{@const tx = tooltipX + 14 > svgWidth - 180 ? tooltipX - 170 : tooltipX + 14}
				<foreignObject
					x={tx}
					y={tooltipY - 36}
					width="170"
					height="40"
					style="pointer-events: none; overflow: visible;"
				>
					<div class="strategy-tooltip">
						{#if tooltip.type === 'stint'}
							<strong>{tooltip.driver}</strong> {tooltip.compound}
							<br />{$t('tooltip.lap')} {tooltip.startLap}-{tooltip.endLap} ({tooltip.laps} {$t('tooltip.laps')})
						{:else}
							<strong>{tooltip.driver}</strong> {$t('tooltip.pit_stop')}
							<br />{$t('tooltip.lap')} {tooltip.lap}
						{/if}
					</div>
				</foreignObject>
			{/if}
		</svg>
	</div>
</div>

<style>
	.strategy-wrap {
		width: 100%;
		overflow-x: auto;
		position: relative;
	}
	:global(.strategy-tooltip) {
		font-family: var(--font-mono);
		font-size: 10px;
		line-height: 1.4;
		color: var(--text-primary);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		padding: 5px 8px;
		border-radius: 4px;
		white-space: nowrap;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
	}
</style>
