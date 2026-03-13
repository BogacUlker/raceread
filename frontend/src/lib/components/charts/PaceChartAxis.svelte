<!--
	SVG axis layer for PaceChart.
	Renders X axis (lap number) and Y axis (time or gap).
-->
<script>
	import { getContext } from 'svelte';

	const { xScale, yScale, width, height, padding } = getContext('LayerCake');

	let { viewMode = 'gap' } = $props();

	let xTicks = $derived(
		(() => {
			const s = $xScale;
			const [min, max] = s.domain();
			const step = max > 40 ? 5 : max > 20 ? 2 : 1;
			const ticks = [];
			for (let i = Math.ceil(min / step) * step; i <= max; i += step) {
				ticks.push(i);
			}
			return ticks;
		})()
	);

	let yTicks = $derived($yScale.ticks(6));
</script>

<g class="axis">
	<!-- X axis -->
	<g class="axis-x" transform="translate(0, {$height})">
		{#each xTicks as tick}
			<g transform="translate({$xScale(tick)}, 0)">
				<line y1="0" y2="5" stroke="var(--border)" />
				<text
					y="16"
					text-anchor="middle"
					fill="var(--text-muted)"
					font-family="var(--font-mono)"
					font-size="12"
				>
					{tick}
				</text>
			</g>
		{/each}
		<!-- X label -->
		<text
			x={$width / 2}
			y="32"
			text-anchor="middle"
			fill="var(--text-muted)"
			font-family="var(--font-mono)"
			font-size="12"
		>
			Lap
		</text>
	</g>

	<!-- Y axis -->
	<g class="axis-y">
		{#each yTicks as tick}
			<g transform="translate(0, {$yScale(tick)})">
				<line x1="0" x2={$width} stroke="var(--border)" stroke-opacity="0.3" />
				<text
					x="-8"
					text-anchor="end"
					dominant-baseline="middle"
					fill="var(--text-muted)"
					font-family="var(--font-mono)"
					font-size="12"
				>
					{viewMode === 'gap'
						? tick === 0
							? '0s'
							: `+${tick.toFixed(1)}s`
						: tick.toFixed(1) + 's'}
				</text>
			</g>
		{/each}
	</g>
</g>
