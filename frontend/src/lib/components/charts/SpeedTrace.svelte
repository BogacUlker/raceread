<!--
	Speed Trace Overlay - two-driver comparison by track distance.
	Raw SVG with d3-zoom for pan/zoom. Energy overlay toggle colors line segments.
-->
<script>
	import { onMount } from 'svelte';
	import { t } from '$lib/i18n/index.js';
	import { scaleLinear } from 'd3-scale';
	import { zoom as d3zoom, zoomIdentity } from 'd3-zoom';
	import { select } from 'd3-selection';
	import { TEAM_COLORS, ENERGY_COLORS } from '$lib/constants.js';
	import InferredBadge from '$lib/components/ui/InferredBadge.svelte';

	let {
		raceId,
		drivers = [],
		circuit = null,
		totalLaps = 58,
		compareDriver1 = '',
		compareDriver2 = '',
	} = $props();

	let containerEl = $state(null);
	let svgEl = $state(null);
	let width = $state(0);
	const margin = { top: 20, right: 20, bottom: 60, left: 50 };
	const mainHeight = 200;
	const gearHeight = 16;
	const throttleHeight = 16;
	const gap = 4;
	const totalHeight = margin.top + mainHeight + gap + gearHeight + gap + throttleHeight + margin.bottom;

	// State
	let driver1 = $state('');
	let driver2 = $state('');
	let selectedLap = $state(5);
	let showEnergy = $state(false);
	let telemetryData = $state({});
	let loading = $state(false);
	let hoverX = $state(null);
	let transform = $state(null);

	// Available laps from totalLaps prop
	let availableLaps = $derived(
		Array.from({ length: totalLaps }, (_, i) => i + 1)
	);

	// Default drivers from props
	$effect(() => {
		if (drivers.length >= 2 && !driver1) {
			driver1 = drivers[0].driver;
			driver2 = drivers[1].driver;
		}
	});

	// Sync from parent compare page when top-level selection changes
	$effect(() => {
		if (compareDriver1 && compareDriver1 !== driver1) {
			driver1 = compareDriver1;
		}
	});
	$effect(() => {
		if (compareDriver2 && compareDriver2 !== driver2) {
			driver2 = compareDriver2;
		}
	});

	// Fetch telemetry when drivers/lap change
	$effect(() => {
		if (driver1 && driver2 && selectedLap) {
			fetchComparison();
		}
	});

	function getApiBase() {
		return import.meta.env.VITE_API_URL || 'http://localhost:8000';
	}

	async function fetchComparison() {
		loading = true;
		try {
			const base = getApiBase();
			const res = await fetch(
				`${base}/api/races/${raceId}/telemetry/compare?d1=${driver1}&d2=${driver2}&lap=${selectedLap}`
			);
			if (res.ok) {
				telemetryData = await res.json();
			}
		} catch { /* ignore */ }
		loading = false;
	}

	// Derived data
	let d1Data = $derived(telemetryData[driver1]?.samples || []);
	let d2Data = $derived(telemetryData[driver2]?.samples || []);
	let d1Team = $derived(telemetryData[driver1]?.team || '');
	let d2Team = $derived(telemetryData[driver2]?.team || '');
	let trackLength = $derived(circuit?.track_length || (d1Data.length > 0 ? d1Data[d1Data.length - 1]?.dist || 5000 : 5000));

	let innerWidth = $derived(width - margin.left - margin.right);
	let xScale = $derived(scaleLinear().domain([0, trackLength]).range([0, innerWidth]));
	let yScale = $derived(scaleLinear().domain([0, 350]).range([mainHeight, 0]));

	// Apply zoom transform
	let zoomedXScale = $derived.by(() => {
		if (transform) {
			return transform.rescaleX(xScale);
		}
		return xScale;
	});

	function getColor(team) {
		return TEAM_COLORS[team] || '#888';
	}

	function energyColor(state) {
		const map = { D: ENERGY_COLORS.deploy, H: ENERGY_COLORS.harvest, C: ENERGY_COLORS.clip, N: ENERGY_COLORS.neutral };
		return map[state] || ENERGY_COLORS.neutral;
	}

	function buildPath(samples, xs) {
		if (!samples.length) return '';
		return samples.map((s, i) => {
			const x = xs(s.dist || 0);
			const y = yScale(s.speed || 0);
			return `${i === 0 ? 'M' : 'L'}${x},${y}`;
		}).join('');
	}

	function buildEnergySegments(samples, xs) {
		if (samples.length < 2) return [];
		const segs = [];
		for (let i = 0; i < samples.length - 1; i++) {
			segs.push({
				x1: xs(samples[i].dist || 0),
				y1: yScale(samples[i].speed || 0),
				x2: xs(samples[i + 1].dist || 0),
				y2: yScale(samples[i + 1].speed || 0),
				color: energyColor(samples[i].energy),
			});
		}
		return segs;
	}

	// Gear strip
	const GEAR_COLORS = ['#6B7280', '#3B82F6', '#22C55E', '#84CC16', '#EAB308', '#F97316', '#EF4444', '#DC2626', '#991B1B'];

	function buildGearBlocks(samples, xs, stripY) {
		if (samples.length < 2) return [];
		const blocks = [];
		for (let i = 0; i < samples.length - 1; i++) {
			const x1 = xs(samples[i].dist || 0);
			const x2 = xs(samples[i + 1].dist || 0);
			const gear = samples[i].gear || 0;
			blocks.push({
				x: x1, w: Math.max(1, x2 - x1), y: stripY,
				fill: GEAR_COLORS[gear] || '#6B7280',
			});
		}
		return blocks;
	}

	// Throttle/brake strip
	function buildThrottleBrakeBlocks(samples, xs, stripY) {
		if (samples.length < 2) return [];
		const blocks = [];
		for (let i = 0; i < samples.length - 1; i++) {
			const x1 = xs(samples[i].dist || 0);
			const x2 = xs(samples[i + 1].dist || 0);
			let fill = '#1A1D27';
			if (samples[i].brake) fill = '#EF4444';
			else if ((samples[i].throttle || 0) > 50) fill = '#22C55E';
			blocks.push({ x: x1, w: Math.max(1, x2 - x1), y: stripY, fill });
		}
		return blocks;
	}

	// Corner markers
	let cornerMarkers = $derived.by(() => {
		if (!circuit?.corners) return [];
		const xs = zoomedXScale;
		return circuit.corners.map(c => ({
			x: xs(c.distance || 0),
			label: `${c.number}${c.letter || ''}`,
		}));
	});

	// Hover
	function handleMouseMove(e) {
		if (!svgEl) return;
		const rect = svgEl.getBoundingClientRect();
		hoverX = e.clientX - rect.left - margin.left;
	}

	function handleMouseLeave() {
		hoverX = null;
	}

	let hoverInfo = $derived.by(() => {
		if (hoverX === null || !d1Data.length) return null;
		const xs = zoomedXScale;
		const dist = xs.invert(hoverX);
		// Find nearest sample for each driver
		const find = (samples) => {
			let best = samples[0];
			let bestDiff = Infinity;
			for (const s of samples) {
				const diff = Math.abs((s.dist || 0) - dist);
				if (diff < bestDiff) { bestDiff = diff; best = s; }
			}
			return best;
		};
		const s1 = d1Data.length ? find(d1Data) : null;
		const s2 = d2Data.length ? find(d2Data) : null;
		return { dist: Math.round(dist), s1, s2, screenX: hoverX };
	});

	// ResizeObserver
	onMount(() => {
		if (!containerEl) return;
		const ro = new ResizeObserver((entries) => {
			for (const entry of entries) {
				width = entry.contentRect.width;
			}
		});
		ro.observe(containerEl);

		return () => ro.disconnect();
	});

	// d3-zoom setup
	$effect(() => {
		if (!svgEl || !innerWidth) return;
		const zoomBehavior = d3zoom()
			.scaleExtent([1, 20])
			.translateExtent([[0, 0], [innerWidth, mainHeight]])
			.extent([[0, 0], [innerWidth, mainHeight]])
			.on('zoom', (event) => {
				transform = event.transform;
			});

		select(svgEl).call(zoomBehavior);
	});
</script>

<div class="chart-card" bind:this={containerEl}>
	<div class="chart-card__header">
		<h3 class="chart-card__title">{$t('charts.speed_trace')}</h3>
		{#if showEnergy}
			<InferredBadge />
		{/if}
	</div>

	<!-- Controls -->
	<div class="speed-trace__controls">
		<div class="speed-trace__selectors">
			<!-- Driver 1 -->
			<select bind:value={driver1} class="speed-trace__select">
				{#each drivers as d}
					<option value={d.driver}>{d.driver}</option>
				{/each}
			</select>
			<span class="speed-trace__vs">{$t('charts.vs')}</span>
			<!-- Driver 2 -->
			<select bind:value={driver2} class="speed-trace__select">
				{#each drivers as d}
					<option value={d.driver}>{d.driver}</option>
				{/each}
			</select>
			<!-- Lap -->
			<select bind:value={selectedLap} class="speed-trace__select">
				{#each availableLaps as lap}
					<option value={lap}>{$t('tooltip.lap')} {lap}</option>
				{/each}
			</select>
		</div>
		<label class="speed-trace__toggle">
			<input type="checkbox" bind:checked={showEnergy} />
			<span>{$t('charts.show_energy')}</span>
		</label>
	</div>

	{#if loading}
		<div class="speed-trace__loading">{$t('common.loading')}</div>
	{:else if d1Data.length === 0 && d2Data.length === 0}
		<div class="speed-trace__loading">{$t('common.no_data')}</div>
	{:else}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<svg
			bind:this={svgEl}
			{width}
			height={totalHeight}
			class="chart-interactive"
			onmousemove={handleMouseMove}
			onmouseleave={handleMouseLeave}
		>
			<g transform="translate({margin.left},{margin.top})">
				<!-- Y axis -->
				{#each [0, 50, 100, 150, 200, 250, 300, 350] as tick}
					<line x1={0} y1={yScale(tick)} x2={innerWidth} y2={yScale(tick)} stroke="var(--border)" stroke-opacity="0.3" />
					<text x={-8} y={yScale(tick)} fill="var(--text-muted)" font-size="10" text-anchor="end" dominant-baseline="middle" font-family="var(--font-mono)">{tick}</text>
				{/each}

				<!-- Corner markers -->
				{#each cornerMarkers as marker}
					{#if marker.x >= 0 && marker.x <= innerWidth}
						<line x1={marker.x} y1={mainHeight} x2={marker.x} y2={mainHeight + gap + gearHeight + gap + throttleHeight} stroke="var(--text-muted)" stroke-opacity="0.3" stroke-dasharray="2,2" />
						<text x={marker.x} y={mainHeight + gap + gearHeight + gap + throttleHeight + 12} fill="var(--text-muted)" font-size="9" text-anchor="middle" font-family="var(--font-mono)">
							{marker.label}
						</text>
					{/if}
				{/each}

				<!-- Speed lines -->
				{#if showEnergy}
					<!-- Energy-colored segments for driver 1 -->
					{#each buildEnergySegments(d1Data, zoomedXScale) as seg}
						<line x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2} stroke={seg.color} stroke-width="2" />
					{/each}
					<!-- Energy-colored segments for driver 2 -->
					{#each buildEnergySegments(d2Data, zoomedXScale) as seg}
						<line x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2} stroke={seg.color} stroke-width="2" stroke-opacity="0.6" stroke-dasharray="4,2" />
					{/each}
				{:else}
					<!-- Team-colored paths -->
					<path d={buildPath(d1Data, zoomedXScale)} fill="none" stroke={getColor(d1Team)} stroke-width="2" />
					<path d={buildPath(d2Data, zoomedXScale)} fill="none" stroke={getColor(d2Team)} stroke-width="2" stroke-opacity="0.8" stroke-dasharray="4,2" />
				{/if}

				<!-- Gear strip (driver 1) -->
				{#each buildGearBlocks(d1Data, zoomedXScale, mainHeight + gap) as block}
					<rect x={block.x} y={block.y} width={block.w} height={gearHeight / 2} fill={block.fill} />
				{/each}
				{#each buildGearBlocks(d2Data, zoomedXScale, mainHeight + gap + gearHeight / 2) as block}
					<rect x={block.x} y={block.y} width={block.w} height={gearHeight / 2} fill={block.fill} opacity="0.7" />
				{/each}

				<!-- Throttle/brake strip (driver 1) -->
				{#each buildThrottleBrakeBlocks(d1Data, zoomedXScale, mainHeight + gap + gearHeight + gap) as block}
					<rect x={block.x} y={block.y} width={block.w} height={throttleHeight / 2} fill={block.fill} />
				{/each}
				{#each buildThrottleBrakeBlocks(d2Data, zoomedXScale, mainHeight + gap + gearHeight + gap + throttleHeight / 2) as block}
					<rect x={block.x} y={block.y} width={block.w} height={throttleHeight / 2} fill={block.fill} opacity="0.7" />
				{/each}

				<!-- Hover crosshair -->
				{#if hoverInfo}
					{@const info = hoverInfo}
					<line x1={info.screenX} y1={0} x2={info.screenX} y2={mainHeight + gap + gearHeight + gap + throttleHeight} stroke="var(--text-secondary)" stroke-width="1" stroke-dasharray="3,3" />

					<!-- Tooltip card -->
					<foreignObject
						x={info.screenX > innerWidth / 2 ? info.screenX - 160 : info.screenX + 10}
						y={10}
						width="150"
						height="120"
					>
						<div class="speed-trace__tooltip">
							<div class="speed-trace__tooltip-dist">{info.dist}m</div>
							{#if info.s1}
								<div class="speed-trace__tooltip-row" style="color:{getColor(d1Team)}">
									{driver1}: {info.s1.speed?.toFixed(0)} km/h
								</div>
							{/if}
							{#if info.s2}
								<div class="speed-trace__tooltip-row" style="color:{getColor(d2Team)}">
									{driver2}: {info.s2.speed?.toFixed(0)} km/h
								</div>
							{/if}
							{#if info.s1 && info.s2}
								{@const delta = (info.s1.speed || 0) - (info.s2.speed || 0)}
								<div class="speed-trace__tooltip-delta">
									{delta >= 0 ? '+' : ''}{delta.toFixed(0)} km/h
								</div>
							{/if}
						</div>
					</foreignObject>
				{/if}

				<!-- X axis label -->
				<text x={innerWidth / 2} y={mainHeight + gap + gearHeight + gap + throttleHeight + 28} fill="var(--text-muted)" font-size="11" text-anchor="middle" font-family="var(--font-mono)">
					{$t('charts.distance')} (m)
				</text>
			</g>

			<!-- Legend -->
			<g transform="translate({margin.left},{totalHeight - 12})">
				<rect x={0} y={-4} width={10} height={3} fill={getColor(d1Team)} />
				<text x={14} y={0} fill="var(--text-secondary)" font-size="10" font-family="var(--font-mono)">{driver1}</text>
				<rect x={60} y={-4} width={10} height={3} fill={getColor(d2Team)} />
				<text x={74} y={0} fill="var(--text-secondary)" font-size="10" font-family="var(--font-mono)">{driver2}</text>
			</g>
		</svg>
	{/if}
</div>

<style>
	.speed-trace__controls {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-sm);
		margin-bottom: var(--space-md);
		flex-wrap: wrap;
	}
	.speed-trace__selectors {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		flex-wrap: wrap;
	}
	.speed-trace__select {
		font-family: var(--font-mono);
		font-size: var(--font-size-small);
		background: var(--bg-secondary);
		color: var(--text-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 4px 8px;
		cursor: pointer;
	}
	.speed-trace__vs {
		font-family: var(--font-mono);
		font-size: var(--font-size-small);
		color: var(--text-muted);
	}
	.speed-trace__toggle {
		display: flex;
		align-items: center;
		gap: 6px;
		font-family: var(--font-mono);
		font-size: var(--font-size-small);
		color: var(--text-secondary);
		cursor: pointer;
	}
	.speed-trace__toggle input {
		accent-color: var(--energy-deploy);
	}
	.speed-trace__loading {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 200px;
		font-family: var(--font-mono);
		font-size: 14px;
		color: var(--text-muted);
	}
	.speed-trace__tooltip {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 6px 8px;
		font-family: var(--font-mono);
		font-size: 10px;
	}
	.speed-trace__tooltip-dist {
		color: var(--text-muted);
		margin-bottom: 4px;
	}
	.speed-trace__tooltip-row {
		line-height: 1.6;
	}
	.speed-trace__tooltip-delta {
		color: var(--text-secondary);
		margin-top: 4px;
		font-weight: 500;
	}

	@media (max-width: 768px) {
		.speed-trace__controls {
			flex-direction: column;
			align-items: stretch;
		}
		.speed-trace__select {
			min-height: 40px;
		}
	}
</style>
