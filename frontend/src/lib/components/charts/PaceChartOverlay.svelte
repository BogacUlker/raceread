<!--
	SVG overlay layer for SC/VSC shaded regions.
	Hover on VSC rect shows lap range tooltip.
-->
<script>
	import { getContext } from 'svelte';
	import { t } from '$lib/i18n/index.js';

	const { xScale, height } = getContext('LayerCake');

	/** @type {{ vscLaps: number[] }} */
	let { vscLaps = [] } = $props();

	let hoveredRange = $state(null);
	let tooltipX = $state(0);
	let tooltipY = $state(0);

	/**
	 * Group consecutive laps into ranges for shading.
	 */
	let ranges = $derived(
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

<g class="vsc-overlay">
	{#each ranges as range}
		{@const x1 = $xScale(range.start - 0.5)}
		{@const x2 = $xScale(range.end + 0.5)}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<rect
			x={x1}
			y="0"
			width={x2 - x1}
			height={$height}
			fill="#F59E0B"
			fill-opacity="0.08"
			style="cursor: pointer;"
			onmouseenter={(e) => handleRangeEnter(range, e)}
			onmousemove={handleRangeMove}
			onmouseleave={handleRangeLeave}
		/>
		<text
			x={(x1 + x2) / 2}
			y="12"
			text-anchor="middle"
			fill="#F59E0B"
			font-family="var(--font-mono)"
			font-size="9"
			opacity="0.6"
			style="pointer-events: none;"
		>
			VSC
		</text>
	{/each}

	<!-- VSC hover tooltip via foreignObject -->
	{#if hoveredRange}
		<foreignObject
			x={tooltipX + 10}
			y={tooltipY - 28}
			width="140"
			height="28"
			style="pointer-events: none; overflow: visible;"
		>
			<div class="vsc-tooltip">
				{$t('tooltip.vsc_active')} {$t('tooltip.lap')} {hoveredRange.start}-{hoveredRange.end}
			</div>
		</foreignObject>
	{/if}
</g>

<style>
	.vsc-tooltip {
		font-family: var(--font-mono);
		font-size: 10px;
		color: #000;
		background: #F59E0B;
		padding: 3px 8px;
		border-radius: 3px;
		white-space: nowrap;
		font-weight: 600;
	}
</style>
