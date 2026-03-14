<!--
	Track Map - circuit outline colored by speed or energy state.
	Single driver, single lap. SVG with aspect-ratio-preserving scale.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { scaleLinear } from 'd3-scale';
	import { interpolateRdYlBu } from 'd3-scale-chromatic';
	import { ENERGY_COLORS } from '$lib/constants.js';
	import InferredBadge from '$lib/components/ui/InferredBadge.svelte';

	let {
		raceId,
		drivers = [],
		circuit = null,
		totalLaps = 58,
	} = $props();

	let selectedDriver = $state('');
	let selectedLap = $state(5);
	let colorMode = $state('speed');
	let telemetryData = $state(null);
	let loading = $state(false);
	let hoverIdx = $state(null);

	// Available laps from totalLaps prop
	let availableLaps = $derived(
		Array.from({ length: totalLaps }, (_, i) => i + 1)
	);

	// Default driver
	$effect(() => {
		if (drivers.length > 0 && !selectedDriver) {
			selectedDriver = drivers[0].driver;
		}
	});

	// Load lap telemetry
	$effect(() => {
		if (selectedDriver && selectedLap && raceId) {
			loadLapData();
		}
	});

	function getApiBase() {
		return import.meta.env.VITE_API_URL || 'http://localhost:8000';
	}

	async function loadLapData() {
		loading = true;
		try {
			const res = await fetch(`${getApiBase()}/api/races/${raceId}/telemetry?driver=${selectedDriver}&lap=${selectedLap}`);
			if (res.ok) {
				telemetryData = await res.json();
			}
		} catch { /* ignore */ }
		loading = false;
	}

	let samples = $derived(telemetryData?.laps?.[0]?.samples || []);

	// Compute bounds from samples or circuit outline
	let bounds = $derived.by(() => {
		const points = samples.length > 0 ? samples : (circuit?.outline || []);
		if (!points.length) return { minX: 0, maxX: 1, minY: 0, maxY: 1 };
		let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
		for (const p of points) {
			if (p.x != null && p.y != null) {
				minX = Math.min(minX, p.x);
				maxX = Math.max(maxX, p.x);
				minY = Math.min(minY, p.y);
				maxY = Math.max(maxY, p.y);
			}
		}
		// Add padding
		const padX = (maxX - minX) * 0.05;
		const padY = (maxY - minY) * 0.05;
		return { minX: minX - padX, maxX: maxX + padX, minY: minY - padY, maxY: maxY + padY };
	});

	// SVG dimensions preserving aspect ratio
	const svgWidth = 500;
	let svgHeight = $derived.by(() => {
		const aspect = (bounds.maxY - bounds.minY) / (bounds.maxX - bounds.minX);
		return Math.max(300, Math.min(600, svgWidth * aspect));
	});

	let xScale = $derived.by(() => {
		return scaleLinear().domain([bounds.minX, bounds.maxX]).range([40, svgWidth - 40]);
	});

	let yScale = $derived.by(() => {
		return scaleLinear().domain([bounds.minY, bounds.maxY]).range([svgHeight - 40, 40]);
	});

	// Speed color scale
	let speedScale = $derived.by(() => {
		const speeds = samples.map(s => s.speed || 0).filter(s => s > 0);
		const min = Math.min(...speeds, 0);
		const max = Math.max(...speeds, 350);
		return scaleLinear().domain([min, max]).range([0, 1]);
	});

	function getSegmentColor(sample) {
		if (colorMode === 'energy') {
			const map = { D: ENERGY_COLORS.deploy, H: ENERGY_COLORS.harvest, C: ENERGY_COLORS.clip, N: ENERGY_COLORS.neutral };
			return map[sample.energy] || ENERGY_COLORS.neutral;
		}
		// Speed mode: blue (slow) to red (fast), reversed for intuition
		const t = speedScale(sample.speed || 0);
		return interpolateRdYlBu(1 - t);
	}

	// Track segments from samples
	let segments = $derived.by(() => {
		if (samples.length < 2) return [];
		const xs = xScale;
		const ys = yScale;
		const segs = [];
		for (let i = 0; i < samples.length - 1; i++) {
			const s1 = samples[i];
			const s2 = samples[i + 1];
			if (s1.x == null || s1.y == null || s2.x == null || s2.y == null) continue;
			segs.push({
				x1: xs(s1.x), y1: ys(s1.y),
				x2: xs(s2.x), y2: ys(s2.y),
				color: getSegmentColor(s1),
				idx: i,
			});
		}
		return segs;
	});

	// Corner labels
	let cornerLabels = $derived.by(() => {
		if (!circuit?.corners) return [];
		const xs = xScale;
		const ys = yScale;
		return circuit.corners.map(c => ({
			x: xs(c.x),
			y: ys(c.y),
			label: `${c.number}`,
		}));
	});

	function handleSegmentHover(idx) {
		hoverIdx = idx;
	}

	let hoverSample = $derived(hoverIdx !== null ? samples[hoverIdx] : null);
</script>

<div class="chart-card">
	<div class="chart-card__header">
		<h3 class="chart-card__title">{$t('charts.track_map')}</h3>
		{#if colorMode === 'energy'}
			<InferredBadge />
		{/if}
	</div>

	<!-- Controls -->
	<div class="track-map__controls">
		<select bind:value={selectedDriver} class="track-map__select">
			{#each drivers as d}
				<option value={d.driver}>{d.driver}</option>
			{/each}
		</select>
		<select bind:value={selectedLap} class="track-map__select">
			{#each availableLaps as lap}
				<option value={lap}>{$t('tooltip.lap')} {lap}</option>
			{/each}
		</select>
		<div class="track-map__mode-toggle">
			<button class="track-map__mode-btn" class:active={colorMode === 'speed'} onclick={() => colorMode = 'speed'}>
				{$t('charts.color_speed')}
			</button>
			<button class="track-map__mode-btn" class:active={colorMode === 'energy'} onclick={() => colorMode = 'energy'}>
				{$t('charts.color_energy')}
			</button>
		</div>
	</div>

	{#if loading}
		<div class="track-map__loading">{$t('common.loading')}</div>
	{:else if samples.length === 0}
		<div class="track-map__loading">{$t('common.no_data')}</div>
	{:else}
		<div class="track-map__container">
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<svg viewBox="0 0 {svgWidth} {svgHeight}" class="track-map__svg" onmouseleave={() => hoverIdx = null}>
				<!-- Track segments -->
				{#each segments as seg}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<line
						x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2}
						stroke={seg.color}
						stroke-width={hoverIdx === seg.idx ? 6 : 4}
						stroke-linecap="round"
						onmouseenter={() => handleSegmentHover(seg.idx)}
					/>
				{/each}

				<!-- Corner labels -->
				{#each cornerLabels as c}
					<circle cx={c.x} cy={c.y} r="8" fill="var(--bg-card)" stroke="var(--text-muted)" stroke-width="1" />
					<text x={c.x} y={c.y} fill="var(--text-secondary)" font-size="8" text-anchor="middle" dominant-baseline="central" font-family="var(--font-mono)">
						{c.label}
					</text>
				{/each}

				<!-- Start/finish marker -->
				{#if samples.length > 0 && samples[0].x != null}
					<circle cx={xScale(samples[0].x)} cy={yScale(samples[0].y)} r="5" fill="var(--accent)" />
				{/if}
			</svg>

			<!-- Hover tooltip -->
			{#if hoverSample}
				<div class="track-map__tooltip">
					<div>{$t('charts.speed')}: {hoverSample.speed?.toFixed(0)} km/h</div>
					<div>{$t('charts.gear')}: {hoverSample.gear}</div>
					<div>{$t('charts.throttle')}: {hoverSample.throttle?.toFixed(0)}%</div>
					<div>{$t('charts.brake')}: {hoverSample.brake ? 'ON' : '-'}</div>
					{#if hoverSample.energy}
						<div>Energy: {hoverSample.energy}</div>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Color legend -->
		{#if colorMode === 'speed'}
			<div class="track-map__legend">
				<span class="track-map__legend-label">0</span>
				<div class="track-map__gradient"></div>
				<span class="track-map__legend-label">350 km/h</span>
			</div>
		{:else}
			<div class="track-map__legend">
				<span class="track-map__legend-chip" style="background:{ENERGY_COLORS.deploy}">D</span>
				<span class="track-map__legend-chip" style="background:{ENERGY_COLORS.harvest}">H</span>
				<span class="track-map__legend-chip" style="background:{ENERGY_COLORS.clip}">C</span>
				<span class="track-map__legend-chip" style="background:{ENERGY_COLORS.neutral}">N</span>
			</div>
		{/if}
	{/if}
</div>

<style>
	.track-map__controls {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		margin-bottom: var(--space-md);
		flex-wrap: wrap;
	}
	.track-map__select {
		font-family: var(--font-mono);
		font-size: var(--font-size-small);
		background: var(--bg-secondary);
		color: var(--text-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 4px 8px;
		cursor: pointer;
	}
	.track-map__mode-toggle {
		display: flex;
		gap: 2px;
		margin-left: auto;
	}
	.track-map__mode-btn {
		font-family: var(--font-mono);
		font-size: var(--font-size-small);
		padding: 4px 10px;
		border: 1px solid var(--border);
		background: transparent;
		color: var(--text-muted);
		cursor: pointer;
		transition: all 0.15s;
	}
	.track-map__mode-btn:first-child { border-radius: var(--radius-sm) 0 0 var(--radius-sm); }
	.track-map__mode-btn:last-child { border-radius: 0 var(--radius-sm) var(--radius-sm) 0; }
	.track-map__mode-btn.active {
		background: var(--bg-secondary);
		color: var(--text-primary);
		border-color: var(--text-muted);
	}
	.track-map__loading {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 300px;
		font-family: var(--font-mono);
		color: var(--text-muted);
	}
	.track-map__container {
		position: relative;
	}
	.track-map__svg {
		width: 100%;
		max-height: 500px;
	}
	.track-map__tooltip {
		position: absolute;
		top: 10px;
		right: 10px;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 6px 10px;
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--text-secondary);
		line-height: 1.6;
		pointer-events: none;
	}
	.track-map__legend {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		margin-top: var(--space-sm);
		justify-content: center;
	}
	.track-map__legend-label {
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--text-muted);
	}
	.track-map__gradient {
		width: 120px;
		height: 8px;
		border-radius: 4px;
		background: linear-gradient(to right, #4575b4, #ffffbf, #d73027);
	}
	.track-map__legend-chip {
		display: inline-block;
		padding: 2px 8px;
		border-radius: 3px;
		font-family: var(--font-mono);
		font-size: 10px;
		color: #fff;
		font-weight: 600;
	}
</style>
