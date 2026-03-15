<!--
	Strategy Timeline - F1 broadcast-style horizontal bar chart.
	Tire stints per driver, sorted by finishing position.
	Compound colors, tire life circles, pit gap markers, cross-chart sync.
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
	 *   vscLaps: number[],
	 *   scLaps: number[]
	 * }}
	 */
	let { drivers, totalLaps, vscLaps = [], scLaps = [] } = $props();

	const rowHeight = 30;
	const rowGap = 3;
	const barHeight = 24;
	const padding = { top: 30, right: 24, bottom: 28, left: 82 };

	// Determine if text should be light or dark on team color background
	function textOnColor(hex) {
		const r = parseInt(hex.slice(1, 3), 16);
		const g = parseInt(hex.slice(3, 5), 16);
		const b = parseInt(hex.slice(5, 7), 16);
		const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
		return luminance > 0.5 ? '#000' : '#fff';
	}

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

	// Group consecutive laps into ranges
	function groupRanges(laps) {
		if (!laps.length) return [];
		const sorted = [...laps].sort((a, b) => a - b);
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
	}

	// SC takes priority: filter VSC laps that overlap with SC
	let scSet = $derived(new Set(scLaps));
	let filteredVscLaps = $derived(vscLaps.filter(l => !scSet.has(l)));

	let vscRanges = $derived(groupRanges(filteredVscLaps));
	let scRanges = $derived(groupRanges(scLaps));

	// Cross-chart sync
	let syncLap = $state(null);
	const unsubLap = hoveredLapStore.subscribe((v) => { syncLap = v; });

	// Hover state
	let hoveredRow = $state(null);

	// Local tooltip state
	let tooltip = $state(null);
	let tooltipX = $state(0);
	let tooltipY = $state(0);

	function handleSvgMouseMove(e) {
		const svg = e.currentTarget;
		const rect = svg.getBoundingClientRect();
		const x = e.clientX - rect.left;

		if (e.target === svg || e.target.classList.contains('strategy-bg')) {
			const lap = Math.round(xScale.invert(x));
			if (lap >= 0 && lap <= totalLaps) {
				hoveredLapStore.set(lap);
			}
		}

		tooltipX = e.clientX - rect.left;
		tooltipY = e.clientY - rect.top;
	}

	function handleSvgMouseLeave() {
		hoveredLapStore.set(null);
		tooltip = null;
		hoveredRow = null;
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
		hoveredRow = driver;
		updateTooltipFromEvent(e);
	}

	function handlePitEnter(driver, pitLap, e) {
		tooltip = {
			type: 'pit',
			driver,
			lap: pitLap
		};
		hoveredRow = driver;
		updateTooltipFromEvent(e);
	}

	function handleElementMove(e) {
		updateTooltipFromEvent(e);
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

	function handleRowEnter(driver) {
		hoveredRow = driver;
	}

	function handleRowLeave() {
		hoveredRow = null;
	}

	function updateTooltipFromEvent(e) {
		const svg = e.currentTarget.closest('svg');
		if (!svg) return;
		const rect = svg.getBoundingClientRect();
		tooltipX = e.clientX - rect.left;
		tooltipY = e.clientY - rect.top;
	}

	// Compound text color - dark text on light compounds
	function compoundTextColor(compound) {
		if (compound === 'HARD') return '#333';
		if (compound === 'MEDIUM') return '#333';
		return '#fff';
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

			<!-- X axis ticks at TOP -->
			{#each xTicks as tick}
				<g transform="translate({xScale(tick)}, {padding.top})">
					<line y1="-4" y2="0" stroke="var(--border)" stroke-width="1" />
					<text
						y="-10"
						text-anchor="middle"
						fill="var(--text-muted)"
						font-family="var(--font-mono)"
						font-size="11"
					>
						{tick}
					</text>
				</g>
			{/each}

			<!-- SC shading (darker amber) -->
			{#each scRanges as range}
				<rect
					x={xScale(range.start - 0.5)}
					y={padding.top}
					width={xScale(range.end + 0.5) - xScale(range.start - 0.5)}
					height={svgHeight - padding.top - padding.bottom}
					fill="#F59E0B"
					fill-opacity="0.07"
					style="pointer-events: none;"
				/>
			{/each}

			<!-- VSC shading (lighter amber) -->
			{#each vscRanges as range}
				<rect
					x={xScale(range.start - 0.5)}
					y={padding.top}
					width={xScale(range.end + 0.5) - xScale(range.start - 0.5)}
					height={svgHeight - padding.top - padding.bottom}
					fill="#F59E0B"
					fill-opacity="0.05"
					style="pointer-events: none;"
				/>
			{/each}

			<!-- Subtle horizontal grid lines -->
			{#each drivers as d, i}
				{@const y = padding.top + i * (rowHeight + rowGap) + rowHeight}
				<line
					x1={padding.left}
					y1={y + 1}
					x2={svgWidth - padding.right}
					y2={y + 1}
					stroke="var(--border)"
					stroke-width="0.5"
					opacity="0.3"
					style="pointer-events: none;"
				/>
			{/each}

			<!-- Driver rows -->
			{#each drivers as d, i}
				{@const y = padding.top + i * (rowHeight + rowGap)}
				{@const color = TEAM_COLORS[d.team] || '#888'}
				{@const isHovered = hoveredRow === d.driver}
				{@const isDimmed = hoveredRow != null && hoveredRow !== d.driver}
				{@const barY = y + (rowHeight - barHeight) / 2}

				<!-- Row hover background -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<rect
					x="0"
					{y}
					width={svgWidth}
					height={rowHeight}
					fill={isHovered ? 'var(--bg-secondary)' : 'transparent'}
					opacity={isHovered ? 0.5 : 0}
					style="pointer-events: none;"
				/>

				<!-- Position number -->
				<text
					x="18"
					y={y + rowHeight / 2}
					text-anchor="end"
					dominant-baseline="middle"
					fill="var(--text-muted)"
					font-family="var(--font-mono)"
					font-size="12"
					font-weight="600"
					opacity={isDimmed ? 0.3 : 0.6}
					style="pointer-events: none;"
				>
					{i + 1}
				</text>

				<!-- Team color badge with driver code -->
				<rect
					x="22"
					y={y + 3}
					width="38"
					height={rowHeight - 6}
					rx="3"
					fill={color}
					opacity={isDimmed ? 0.2 : 0.9}
					style="pointer-events: none;"
				/>
				<text
					x="41"
					y={y + rowHeight / 2}
					text-anchor="middle"
					dominant-baseline="middle"
					fill={textOnColor(color)}
					font-family="var(--font-mono)"
					font-size="12"
					font-weight="700"
					opacity={isDimmed ? 0.3 : 1}
					style="pointer-events: none;"
				>
					{d.driver}
				</text>

				<!-- Stints -->
				{#each d.stints as stint, si}
					{@const sx = xScale(stint.start_lap - 1) + (si > 0 ? 1.5 : 0)}
					{@const sw = xScale(stint.end_lap) - xScale(stint.start_lap - 1) - (si > 0 ? 1.5 : 0)}
					{@const compoundColor = COMPOUND_COLORS[stint.compound] || '#888'}
					{@const isLastStint = si === d.stints.length - 1}
					{@const circleR = 12}
					{@const circleX = sx + sw}

					<!-- Stint bar -->
					<rect
						x={sx}
						y={barY}
						width={Math.max(sw, 2)}
						height={barHeight}
						fill={compoundColor}
						rx="2"
						opacity={isDimmed ? 0.25 : 0.85}
						style="cursor: pointer;"
						onmouseenter={(e) => handleStintEnter(d.driver, stint, e)}
						onmousemove={handleElementMove}
						onmouseleave={handleElementLeave}
					/>

					<!-- Compound letter inside bar (if wide enough) -->
					{#if sw > 30}
						<text
							x={sx + sw / 2}
							y={barY + barHeight / 2}
							text-anchor="middle"
							dominant-baseline="middle"
							fill={compoundTextColor(stint.compound)}
							font-family="var(--font-mono)"
							font-size="13"
							font-weight="800"
							opacity={isDimmed ? 0.3 : 0.95}
							style="pointer-events: none;"
						>
							{stint.compound.charAt(0)}
						</text>
					{/if}

					<!-- Tire life circle at end of last stint -->
					{#if isLastStint && stint.laps > 0}
						<circle
							cx={circleX}
							cy={barY + barHeight / 2}
							r={circleR}
							fill={compoundColor}
							stroke="var(--bg-primary)"
							stroke-width="2"
							opacity={isDimmed ? 0.3 : 1}
							style="pointer-events: none;"
						/>
						<text
							x={circleX}
							y={barY + barHeight / 2}
							text-anchor="middle"
							dominant-baseline="middle"
							fill={compoundTextColor(stint.compound)}
							font-family="var(--font-mono)"
							font-size="11"
							font-weight="700"
							opacity={isDimmed ? 0.3 : 1}
							style="pointer-events: none;"
						>
							{stint.laps}
						</text>
					{/if}
				{/each}

				<!-- Pit stop markers (subtle dashes) -->
				{#each d.pit_laps || [] as pitLap}
					<!-- Invisible wider hit area -->
					<line
						x1={xScale(pitLap)}
						y1={barY - 2}
						x2={xScale(pitLap)}
						y2={barY + barHeight + 2}
						stroke="transparent"
						stroke-width="8"
						style="cursor: pointer;"
						onmouseenter={(e) => handlePitEnter(d.driver, pitLap, e)}
						onmousemove={handleElementMove}
						onmouseleave={handleElementLeave}
					/>
				{/each}

				<!-- Row hover area -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<rect
					x="0"
					{y}
					width={padding.left}
					height={rowHeight}
					fill="transparent"
					style="cursor: pointer;"
					onmouseenter={() => handleRowEnter(d.driver)}
					onmouseleave={handleRowLeave}
				/>
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
					opacity="0.4"
					style="pointer-events: none;"
				/>
			{/if}

			<!-- Tooltip -->
			{#if tooltip}
				{@const tx = tooltipX + 14 > svgWidth - 200 ? tooltipX - 190 : tooltipX + 14}
				<foreignObject
					x={tx}
					y={tooltipY - 40}
					width="190"
					height="48"
					style="pointer-events: none; overflow: visible;"
				>
					<div class="strategy-tooltip">
						{#if tooltip.type === 'stint'}
							<div class="strategy-tooltip__row">
								<strong>{tooltip.driver}</strong>
								<span class="strategy-tooltip__compound" style="background: {COMPOUND_COLORS[tooltip.compound] || '#888'}; color: {compoundTextColor(tooltip.compound)}">
									{tooltip.compound}
								</span>
							</div>
							<div class="strategy-tooltip__detail">
								{$t('tooltip.lap')} {tooltip.startLap}-{tooltip.endLap} &middot; {tooltip.laps} {$t('tooltip.laps')}
							</div>
						{:else}
							<div class="strategy-tooltip__row">
								<strong>{tooltip.driver}</strong>
								<span class="strategy-tooltip__pit">{$t('tooltip.pit_stop')}</span>
							</div>
							<div class="strategy-tooltip__detail">
								{$t('tooltip.lap')} {tooltip.lap}
							</div>
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
		font-size: 11px;
		line-height: 1.4;
		color: var(--text-primary);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		padding: 6px 10px;
		border-radius: var(--radius-sm);
		white-space: nowrap;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
	}
	:global(.strategy-tooltip__row) {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	:global(.strategy-tooltip__compound) {
		font-size: 9px;
		font-weight: 700;
		padding: 1px 5px;
		border-radius: 2px;
		text-transform: uppercase;
	}
	:global(.strategy-tooltip__pit) {
		font-size: 9px;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
	}
	:global(.strategy-tooltip__detail) {
		font-size: 10px;
		color: var(--text-secondary);
		margin-top: 2px;
	}
</style>
