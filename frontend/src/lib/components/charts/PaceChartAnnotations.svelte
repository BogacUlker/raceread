<!--
	SVG layer for annotation diamond markers on PaceChart.
	Renders colored diamonds at annotated laps, positioned via LayerCake scales.
-->
<script>
	import { getContext } from 'svelte';
	import { ANNOTATION_COLORS } from '$lib/constants.js';

	const { xScale, yScale } = getContext('LayerCake');

	/**
	 * @type {{
	 *   annotations: Array<{driver: string|null, lap: number|null, chart_type: string, category: string, severity: string}>,
	 *   driverData: Array<{driver: string, team: string, laps: Array}>,
	 *   yKey: string
	 * }}
	 */
	let { annotations = [], driverData = [], yKey = 'gap' } = $props();

	let markers = $derived(
		annotations
			.filter((a) => a.chart_type === 'pace' && a.driver && a.lap != null)
			.map((a) => {
				const driver = driverData.find((d) => d.driver === a.driver);
				if (!driver) return null;
				const lap = driver.laps.find((l) => l.lap === a.lap);
				if (!lap || lap[yKey] == null) return null;
				return {
					driver: a.driver,
					lap: a.lap,
					category: a.category,
					severity: a.severity,
					yVal: lap[yKey],
					color: ANNOTATION_COLORS[a.category] || '#888'
				};
			})
			.filter(Boolean)
	);
</script>

<g class="annotation-markers">
	{#each markers as m}
		{@const cx = $xScale(m.lap)}
		{@const cy = $yScale(m.yVal)}
		<g transform="translate({cx},{cy})">
			<!-- Diamond marker -->
			<path
				d="M0,-5 L4,0 L0,5 L-4,0 Z"
				fill={m.color}
				stroke="var(--bg-card)"
				stroke-width="1.2"
				opacity="0.9"
				style="pointer-events: none;"
			/>
		</g>
	{/each}
</g>
