<!--
	SVG layers for EnergyTimeline.
	Deploy + clip are the story: drawn as bars on their own scale so they
	stay readable. Harvest (which dominates every lap) becomes a faint
	context band hanging from the top. VSC laps get shaded bands.
-->
<script>
	import { getContext } from 'svelte';
	import { area, curveMonotoneX } from 'd3-shape';
	import { ENERGY_COLORS } from '$lib/constants.js';

	const { data, xScale, yScale, width } = getContext('LayerCake');

	// Deploy+clip get their own scale: season-max fills ~90% of the height
	let maxActive = $derived(
		Math.max(5, ...$data.map((d) => (d.normalized_deploy || 0) + (d.normalized_clip || 0)))
	);
	let k = $derived(90 / maxActive);

	// Harvest as a compressed band from the top (100% harvest = 32 units deep)
	let harvestArea = $derived(
		$data.length > 1
			? area()
				.x((d) => $xScale(d.lap))
				.y0(() => $yScale(100))
				.y1((d) => $yScale(100 - (d.normalized_harvest || 0) * 0.32))
				.curve(curveMonotoneX)($data)
			: null
	);

	let barW = $derived(
		Math.max(2, Math.min(8, ($data.length > 1 ? ($xScale($data[1].lap) - $xScale($data[0].lap)) : 8) * 0.55))
	);

	let bars = $derived(
		$data.map((d) => {
			const dep = (d.normalized_deploy || 0) * k;
			const clip = (d.normalized_clip || 0) * k;
			return {
				lap: d.lap,
				x: $xScale(d.lap),
				depY: $yScale(dep),
				depH: Math.max(0, $yScale(0) - $yScale(dep)),
				clipY: $yScale(dep + clip),
				clipH: Math.max(0, $yScale(dep) - $yScale(dep + clip)),
			};
		})
	);

	// Contiguous VSC laps -> shaded bands
	let vscBands = $derived(
		(() => {
			const bands = [];
			let start = null, prev = null;
			for (const d of $data) {
				if (d.is_vsc) {
					if (start === null) start = d.lap;
					prev = d.lap;
				} else if (start !== null) {
					bands.push({ start, end: prev });
					start = null;
				}
			}
			if (start !== null) bands.push({ start, end: prev });
			return bands;
		})()
	);

	let xTicks = $derived($data.filter((d) => d.lap % 10 === 0).map((d) => d.lap));
</script>

<g class="energy-layers">
	{#if $data.length > 0}
		<!-- VSC bands -->
		{#each vscBands as b}
			<rect
				x={$xScale(b.start) - barW / 2}
				y={$yScale(100)}
				width={$xScale(b.end) - $xScale(b.start) + barW}
				height={$yScale(0) - $yScale(100)}
				fill="#F59E0B"
				opacity="0.07"
			/>
			<text
				x={($xScale(b.start) + $xScale(b.end)) / 2}
				y={$yScale(100) + 10}
				text-anchor="middle"
				font-size="8"
				fill="#F59E0B"
				opacity="0.7"
				font-family="var(--font-mono)"
			>VSC</text>
		{/each}

		<!-- Harvest context band -->
		{#if harvestArea}
			<path d={harvestArea} fill={ENERGY_COLORS.harvest} opacity="0.15" />
		{/if}

		<!-- Deploy + clip bars -->
		{#each bars as b}
			{#if b.depH > 0.5}
				<rect x={b.x - barW / 2} y={b.depY} width={barW} height={b.depH} fill={ENERGY_COLORS.deploy} opacity="0.9" />
			{/if}
			{#if b.clipH > 0.5}
				<rect x={b.x - barW / 2} y={b.clipY} width={barW} height={b.clipH} fill={ENERGY_COLORS.clip} opacity="0.95" />
			{/if}
		{/each}

		<!-- Baseline + lap axis -->
		<line x1="0" x2={$width} y1={$yScale(0)} y2={$yScale(0)} stroke="#2E3240" />
		{#each xTicks as tick}
			<text
				x={$xScale(tick)}
				y={$yScale(0) + 16}
				text-anchor="middle"
				font-size="9"
				fill="#7D8794"
				font-family="var(--font-mono)"
			>L{tick}</text>
		{/each}
	{/if}
</g>
