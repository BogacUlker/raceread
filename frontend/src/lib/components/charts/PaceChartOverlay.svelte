<!--
	SVG overlay layer for SC/VSC shaded regions.
	Both use amber/yellow family (F1 safety car convention).
	SC = full safety car (darker amber), VSC = virtual (lighter amber).
	Overlapping laps: SC takes priority over VSC.
-->
<script>
	import { getContext } from 'svelte';
	import { t } from '$lib/i18n/index.js';

	const { xScale, height } = getContext('LayerCake');

	/** @type {{ vscLaps: number[], scLaps: number[] }} */
	let { vscLaps = [], scLaps = [] } = $props();

	let hoveredRange = $state(null);
	let tooltipX = $state(0);
	let tooltipY = $state(0);

	/**
	 * Group consecutive laps into ranges for shading.
	 */
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

	// Filter VSC laps that are also SC laps (SC takes priority)
	let scSet = $derived(new Set(scLaps));
	let filteredVscLaps = $derived(vscLaps.filter(l => !scSet.has(l)));

	let vscRanges = $derived(groupRanges(filteredVscLaps));
	let scRanges = $derived(groupRanges(scLaps));

	function handleRangeEnter(range, e) {
		hoveredRange = range;
		updateTooltipPos(e);
	}

	function handleRangeMove(e) {
		updateTooltipPos(e);
	}

	function handleRangeLeave() {
		hoveredRange = null;
	}

	function updateTooltipPos(e) {
		const svg = e.currentTarget.closest('svg');
		if (!svg) return;
		const rect = svg.getBoundingClientRect();
		tooltipX = e.clientX - rect.left;
		tooltipY = e.clientY - rect.top;
	}
</script>

<g class="sc-vsc-overlay">
	<!-- SC regions (darker amber) -->
	{#each scRanges as range}
		{@const x1 = $xScale(range.start - 0.5)}
		{@const x2 = $xScale(range.end + 0.5)}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<rect
			x={x1}
			y="0"
			width={x2 - x1}
			height={$height}
			fill="#F59E0B"
			fill-opacity="0.10"
			style="cursor: pointer;"
			onmouseenter={(e) => handleRangeEnter({ ...range, type: 'SC' }, e)}
			onmousemove={handleRangeMove}
			onmouseleave={handleRangeLeave}
		/>
		<text
			x={(x1 + x2) / 2}
			y="12"
			text-anchor="middle"
			fill="#D97706"
			font-family="var(--font-mono)"
			font-size="11"
			font-weight="700"
			opacity="0.9"
			style="pointer-events: none;"
		>
			SC
		</text>
	{/each}

	<!-- VSC regions (lighter amber) -->
	{#each vscRanges as range}
		{@const x1 = $xScale(range.start - 0.5)}
		{@const x2 = $xScale(range.end + 0.5)}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<rect
			x={x1}
			y="0"
			width={x2 - x1}
			height={$height}
			fill="#F59E0B"
			fill-opacity="0.06"
			style="cursor: pointer;"
			onmouseenter={(e) => handleRangeEnter({ ...range, type: 'VSC' }, e)}
			onmousemove={handleRangeMove}
			onmouseleave={handleRangeLeave}
		/>
		<text
			x={(x1 + x2) / 2}
			y="12"
			text-anchor="middle"
			fill="#F59E0B"
			font-family="var(--font-mono)"
			font-size="11"
			font-weight="600"
			opacity="0.8"
			style="pointer-events: none;"
		>
			VSC
		</text>
	{/each}

	<!-- Hover tooltip -->
	{#if hoveredRange}
		{@const isSC = hoveredRange.type === 'SC'}
		<foreignObject
			x={tooltipX + 10}
			y={tooltipY - 28}
			width="180"
			height="28"
			style="pointer-events: none; overflow: visible;"
		>
			<div class="sc-tooltip" class:sc-tooltip--full={isSC}>
				{isSC ? $t('tooltip.sc_active') : $t('tooltip.vsc_active')} - {$t('tooltip.lap')} {hoveredRange.start}-{hoveredRange.end}
			</div>
		</foreignObject>
	{/if}
</g>

<style>
	.sc-tooltip {
		font-family: var(--font-mono);
		font-size: 12px;
		color: #000;
		background: #FCD34D;
		padding: 3px 8px;
		border-radius: 3px;
		white-space: nowrap;
		font-weight: 600;
	}
	.sc-tooltip--full {
		background: #F59E0B;
		color: #000;
	}
</style>
