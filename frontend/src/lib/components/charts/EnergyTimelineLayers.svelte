<!--
	SVG stacked area layers for EnergyTimeline.
	Three stacked areas: deploy, harvest, clip (normalized).
-->
<script>
	import { getContext } from 'svelte';
	import { area } from 'd3-shape';
	import { ENERGY_COLORS } from '$lib/constants.js';

	const { data, xScale, yScale } = getContext('LayerCake');

	// Build stacked values: deploy at bottom, then harvest, then clip on top
	let stackedData = $derived(
		$data.map((d) => {
			const deploy = d.normalized_deploy || 0;
			const harvest = d.normalized_harvest || 0;
			const clip = d.normalized_clip || 0;
			return {
				lap: d.lap,
				// Stack: deploy, then harvest, then clip
				deploy_y0: 0,
				deploy_y1: deploy,
				harvest_y0: deploy,
				harvest_y1: deploy + harvest,
				clip_y0: deploy + harvest,
				clip_y1: deploy + harvest + clip,
			};
		})
	);

	function makeArea(y0Key, y1Key) {
		return area()
			.x((d) => $xScale(d.lap))
			.y0((d) => $yScale(d[y0Key]))
			.y1((d) => $yScale(d[y1Key]));
	}
</script>

<g class="energy-areas">
	{#if stackedData.length > 0}
		<!-- Deploy (bottom) -->
		<path
			d={makeArea('deploy_y0', 'deploy_y1')(stackedData)}
			fill={ENERGY_COLORS.deploy}
			opacity="0.7"
		/>
		<!-- Harvest (middle) -->
		<path
			d={makeArea('harvest_y0', 'harvest_y1')(stackedData)}
			fill={ENERGY_COLORS.harvest}
			opacity="0.7"
		/>
		<!-- Clip (top) -->
		<path
			d={makeArea('clip_y0', 'clip_y1')(stackedData)}
			fill={ENERGY_COLORS.clip}
			opacity="0.7"
		/>
	{/if}
</g>
