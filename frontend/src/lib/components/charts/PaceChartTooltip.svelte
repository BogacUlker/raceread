<!--
	HTML tooltip layer for PaceChart.
	Shows lap details on hover. Emits hoveredLap to shared store for cross-chart sync.
-->
<script>
	import { getContext } from 'svelte';
	import { TEAM_COLORS, COMPOUND_COLORS, ANNOTATION_COLORS } from '$lib/constants.js';
	import { formatLapTime, formatGap } from '$lib/utils/format.js';
	import { hoveredLap as hoveredLapStore } from '$lib/stores/race.js';
	import { locale } from '$lib/i18n/index.js';
	import { t } from '$lib/i18n/index.js';

	const { xScale, yScale, width, height } = getContext('LayerCake');

	/**
	 * @type {{
	 *   driverData: Array<{driver: string, team: string, laps: Array}>,
	 *   viewMode: string,
	 *   annotations: Array,
	 *   vscLaps: number[],
	 *   scLaps: number[]
	 * }}
	 */
	let { driverData, viewMode, annotations = [], vscLaps = [], scLaps = [] } = $props();

	let localHoveredLap = $state(null);
	let mouseX = $state(0);
	let mouseY = $state(0);

	// Sync from external store (other chart hovered)
	let externalLap = $state(null);
	const unsubscribe = hoveredLapStore.subscribe((v) => {
		externalLap = v;
	});

	// The displayed lap: local hover takes priority, else external sync
	let displayLap = $derived(localHoveredLap ?? externalLap);

	// Check if a lap is in a VSC or SC range
	let vscSet = $derived(new Set(vscLaps));
	let scSet = $derived(new Set(scLaps));

	function handleMouseMove(e) {
		const rect = e.currentTarget.getBoundingClientRect();
		const x = e.clientX - rect.left;
		const y = e.clientY - rect.top;
		mouseX = x;
		mouseY = y;

		const domain = $xScale.domain();
		const lapNum = Math.round($xScale.invert(x));
		if (lapNum >= domain[0] && lapNum <= domain[1]) {
			localHoveredLap = lapNum;
			hoveredLapStore.set(lapNum);
		} else {
			localHoveredLap = null;
			hoveredLapStore.set(null);
		}
	}

	function handleMouseLeave() {
		localHoveredLap = null;
		hoveredLapStore.set(null);
	}

	let tooltipData = $derived(
		displayLap
			? driverData
					.map(({ driver, team, laps }) => {
						const lap = laps.find((l) => l.lap === displayLap);
						if (!lap) return null;
						return { driver, team, ...lap };
					})
					.filter(Boolean)
					.sort((a, b) => {
						const aVal = viewMode === 'gap' ? a.gap : a.time_s;
						const bVal = viewMode === 'gap' ? b.gap : b.time_s;
						return (aVal ?? 999) - (bVal ?? 999);
					})
			: []
	);

	// Annotations for the currently hovered lap
	let lapAnnotations = $derived(
		displayLap
			? annotations.filter(
					(a) => a.chart_type === 'pace' && a.lap === displayLap && a.driver
				)
			: []
	);

	let guideX = $derived(displayLap != null ? $xScale(displayLap) : 0);

	let tooltipLeft = $derived(
		mouseX > $width * 0.65 ? mouseX - 260 : mouseX + 16
	);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="tooltip-capture"
	onmousemove={handleMouseMove}
	onmouseleave={handleMouseLeave}
>
	{#if displayLap != null}
		<!-- Vertical guide line -->
		<div
			class="guide-line"
			style="left: {guideX}px; height: {$height}px;"
		></div>

		<!-- Only show tooltip box when locally hovered (not external sync) -->
		{#if localHoveredLap != null && tooltipData.length > 0}
			<div
				class="tooltip"
				style="left: {tooltipLeft}px; top: {mouseY - 10}px;"
			>
				<div class="tooltip__header">
					<span>{$t('tooltip.lap')} {displayLap}</span>
					{#if scSet.has(displayLap)}
						<span class="tooltip__vsc">{$t('tooltip.sc_active')}</span>
					{:else if vscSet.has(displayLap)}
						<span class="tooltip__vsc">{$t('tooltip.vsc_active')}</span>
					{/if}
				</div>
				{#each tooltipData as d}
					{@const color = TEAM_COLORS[d.team] || '#888'}
					{@const compoundColor = d.compound ? COMPOUND_COLORS[d.compound] || '#888' : null}
					<div class="tooltip__row">
						<span class="tooltip__dot" style="background: {color}"></span>
						<span class="tooltip__driver">{d.driver}</span>
						{#if compoundColor}
							<span class="tooltip__compound" style="background: {compoundColor}"></span>
						{/if}
						{#if d.tire_life != null}
							<span class="tooltip__tire-age">L{d.tire_life}</span>
						{/if}
						<span class="tooltip__value">
							{viewMode === 'gap' ? formatGap(d.gap) : formatLapTime(d.time_s)}
						</span>
					</div>
				{/each}
				{#if lapAnnotations.length > 0}
					<div class="tooltip__annotations">
						{#each lapAnnotations as ann}
							{@const annColor = ANNOTATION_COLORS[ann.category] || '#888'}
							<div class="tooltip__ann" style="border-left-color: {annColor}">
								<span class="tooltip__ann-cat" style="color: {annColor}">
									{ann.category.replace('_', ' ')}
								</span>
								<span class="tooltip__ann-driver">{ann.driver}</span>
								<div class="tooltip__ann-text">
									{$locale === 'tr' ? ann.text_tr : ann.text_en}
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	{/if}
</div>

<style>
	.tooltip-capture {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
	}
	.guide-line {
		position: absolute;
		top: 0;
		width: 1px;
		border-left: 1px dashed var(--text-muted);
		opacity: 0.4;
		pointer-events: none;
	}
	.tooltip {
		position: absolute;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: 8px 10px;
		pointer-events: none;
		z-index: 20;
		min-width: 170px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
	}
	.tooltip__header {
		font-family: var(--font-mono);
		font-size: 13px;
		font-weight: 600;
		color: var(--text-secondary);
		margin-bottom: 4px;
		padding-bottom: 4px;
		border-bottom: 1px solid var(--border);
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.tooltip__vsc {
		font-size: 9px;
		font-weight: 700;
		color: #000;
		background: #F59E0B;
		padding: 1px 4px;
		border-radius: 2px;
		text-transform: uppercase;
	}
	.tooltip__row {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 2px 0;
	}
	.tooltip__dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.tooltip__driver {
		font-family: var(--font-mono);
		font-size: 13px;
		font-weight: 500;
		color: var(--text-primary);
		flex: 1;
	}
	.tooltip__compound {
		width: 6px;
		height: 6px;
		border-radius: 1px;
		flex-shrink: 0;
	}
	.tooltip__tire-age {
		font-family: var(--font-mono);
		font-size: 9px;
		color: var(--text-muted);
		flex-shrink: 0;
	}
	.tooltip__value {
		font-family: var(--font-mono);
		font-size: 13px;
		color: var(--text-secondary);
	}
	.tooltip__annotations {
		margin-top: 6px;
		padding-top: 6px;
		border-top: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.tooltip__ann {
		border-left: 2px solid;
		padding-left: 6px;
	}
	.tooltip__ann-cat {
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.tooltip__ann-driver {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-muted);
		margin-left: 4px;
	}
	.tooltip__ann-text {
		font-family: var(--font-mono);
		font-size: 13px;
		line-height: 1.4;
		color: var(--text-secondary);
		max-width: 240px;
	}
</style>
