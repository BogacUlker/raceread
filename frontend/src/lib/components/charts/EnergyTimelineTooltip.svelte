<!--
	HTML tooltip layer for EnergyTimeline.
	Shows energy percentages on hover and syncs hoveredLap across charts.
-->
<script>
	import { getContext } from 'svelte';
	import { ENERGY_COLORS } from '$lib/constants.js';
	import { hoveredLap as hoveredLapStore } from '$lib/stores/race.js';
	import { t } from '$lib/i18n/index.js';
	import { formatPct } from '$lib/utils/format.js';

	const { xScale, yScale, width, height, data } = getContext('LayerCake');

	let localHoveredLap = $state(null);
	let mouseX = $state(0);
	let mouseY = $state(0);

	// Sync from external store
	let externalLap = $state(null);
	const unsubLap = hoveredLapStore.subscribe((v) => { externalLap = v; });

	let displayLap = $derived(localHoveredLap ?? externalLap);

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
		displayLap != null
			? $data.find((d) => d.lap === displayLap) || null
			: null
	);

	let guideX = $derived(displayLap != null ? $xScale(displayLap) : 0);

	let tooltipLeft = $derived(
		mouseX > $width * 0.65 ? mouseX - 170 : mouseX + 16
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

		<!-- Only show tooltip box when locally hovered -->
		{#if localHoveredLap != null && tooltipData}
			<div
				class="tooltip"
				style="left: {tooltipLeft}px; top: {mouseY - 10}px;"
			>
				<div class="tooltip__header">{$t('tooltip.lap')} {displayLap}</div>
				<div class="tooltip__row">
					<span class="tooltip__dot" style="background: {ENERGY_COLORS.deploy}"></span>
					<span class="tooltip__label">{$t('charts.deploy')}</span>
					<span class="tooltip__value">{formatPct(tooltipData.normalized_deploy || 0)}</span>
				</div>
				<div class="tooltip__row">
					<span class="tooltip__dot" style="background: {ENERGY_COLORS.harvest}"></span>
					<span class="tooltip__label">{$t('charts.harvest')}</span>
					<span class="tooltip__value">{formatPct(tooltipData.normalized_harvest || 0)}</span>
				</div>
				<div class="tooltip__row">
					<span class="tooltip__dot" style="background: {ENERGY_COLORS.clip}"></span>
					<span class="tooltip__label">{$t('charts.clip')}</span>
					<span class="tooltip__value">{formatPct(tooltipData.normalized_clip || 0)}</span>
				</div>
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
		min-width: 150px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
	}
	.tooltip__header {
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 600;
		color: var(--text-secondary);
		margin-bottom: 4px;
		padding-bottom: 4px;
		border-bottom: 1px solid var(--border);
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
		border-radius: 2px;
		flex-shrink: 0;
	}
	.tooltip__label {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-primary);
		flex: 1;
	}
	.tooltip__value {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-secondary);
	}
</style>
