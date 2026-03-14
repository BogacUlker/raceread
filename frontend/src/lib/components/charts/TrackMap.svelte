<!--
	Track Map - circuit outline colored by speed or energy state.
	Single driver, single lap. SVG with aspect-ratio-preserving scale.
-->
<script>
	import { onMount } from 'svelte';
	import { t } from '$lib/i18n/index.js';
	import { scaleLinear } from 'd3-scale';
	import { interpolateTurbo } from 'd3-scale-chromatic';
	import { ENERGY_COLORS } from '$lib/constants.js';
	import InferredBadge from '$lib/components/ui/InferredBadge.svelte';

	let {
		raceId,
		drivers = [],
		circuit = null,
		totalLaps = 58,
	} = $props();

	let containerEl = $state(null);
	let containerWidth = $state(500);
	let selectedDriver = $state('');
	let selectedLap = $state(5);
	let colorMode = $state('speed');
	let telemetryData = $state(null);
	let loading = $state(false);
	let hoverIdx = $state(null);

	const TRACK_WIDTH = 7;
	const TRACK_WIDTH_HOVER = 10;
	const CORNER_OFFSET = 22;

	let availableLaps = $derived(
		Array.from({ length: totalLaps }, (_, i) => i + 1)
	);

	$effect(() => {
		if (drivers.length > 0 && !selectedDriver) {
			selectedDriver = drivers[0].driver;
		}
	});

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

	// Compute bounds with padding for corner labels
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
		const padX = (maxX - minX) * 0.08;
		const padY = (maxY - minY) * 0.08;
		return { minX: minX - padX, maxX: maxX + padX, minY: minY - padY, maxY: maxY + padY };
	});

	// Track center for corner label offset direction
	let trackCenter = $derived.by(() => {
		const points = samples.length > 0 ? samples : (circuit?.outline || []);
		if (!points.length) return { x: 0, y: 0 };
		let sx = 0, sy = 0, n = 0;
		for (const p of points) {
			if (p.x != null && p.y != null) { sx += p.x; sy += p.y; n++; }
		}
		return { x: sx / n, y: sy / n };
	});

	let svgWidth = $derived(Math.max(300, containerWidth));
	let svgHeight = $derived.by(() => {
		const aspect = (bounds.maxY - bounds.minY) / (bounds.maxX - bounds.minX);
		return Math.max(300, Math.min(650, svgWidth * aspect));
	});

	let xScale = $derived.by(() => {
		return scaleLinear().domain([bounds.minX, bounds.maxX]).range([50, svgWidth - 50]);
	});

	let yScale = $derived.by(() => {
		return scaleLinear().domain([bounds.minY, bounds.maxY]).range([svgHeight - 50, 50]);
	});

	// Speed range from actual data
	let speedRange = $derived.by(() => {
		const speeds = samples.map(s => s.speed || 0).filter(s => s > 0);
		if (!speeds.length) return { min: 0, max: 350 };
		return { min: Math.min(...speeds), max: Math.max(...speeds) };
	});

	let speedScale = $derived.by(() => {
		return scaleLinear().domain([speedRange.min, speedRange.max]).range([0.05, 0.95]);
	});

	function getSegmentColor(sample) {
		if (colorMode === 'energy') {
			const map = { D: ENERGY_COLORS.deploy, H: ENERGY_COLORS.harvest, C: ENERGY_COLORS.clip, N: ENERGY_COLORS.neutral };
			return map[sample.energy] || ENERGY_COLORS.neutral;
		}
		const t = speedScale(sample.speed || 0);
		return interpolateTurbo(t);
	}

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

	// Corner labels offset away from track center
	let cornerLabels = $derived.by(() => {
		if (!circuit?.corners) return [];
		const xs = xScale;
		const ys = yScale;
		const cx = xs(trackCenter.x);
		const cy = ys(trackCenter.y);

		return circuit.corners.map(c => {
			const px = xs(c.x);
			const py = ys(c.y);
			// Direction away from center
			const dx = px - cx;
			const dy = py - cy;
			const len = Math.sqrt(dx * dx + dy * dy) || 1;
			const nx = dx / len;
			const ny = dy / len;
			return {
				trackX: px,
				trackY: py,
				labelX: px + nx * CORNER_OFFSET,
				labelY: py + ny * CORNER_OFFSET,
				label: `${c.number}`,
			};
		});
	});

	// Start/finish position
	let startPos = $derived.by(() => {
		if (!samples.length || samples[0].x == null) return null;
		return { x: xScale(samples[0].x), y: yScale(samples[0].y) };
	});

	// Hover indicator position
	let hoverPos = $derived.by(() => {
		if (hoverIdx === null || !samples[hoverIdx]) return null;
		const s = samples[hoverIdx];
		if (s.x == null || s.y == null) return null;
		return { x: xScale(s.x), y: yScale(s.y) };
	});

	function handleSegmentHover(idx) {
		hoverIdx = idx;
	}

	let hoverSample = $derived(hoverIdx !== null ? samples[hoverIdx] : null);

	// Speed legend ticks
	let speedTicks = $derived.by(() => {
		const { min, max } = speedRange;
		const step = 50;
		const ticks = [];
		const start = Math.ceil(min / step) * step;
		for (let v = start; v <= max; v += step) {
			ticks.push(v);
		}
		return ticks;
	});

	onMount(() => {
		if (!containerEl) return;
		const ro = new ResizeObserver((entries) => {
			for (const entry of entries) {
				containerWidth = entry.contentRect.width;
			}
		});
		ro.observe(containerEl);
		return () => ro.disconnect();
	});
</script>

<div class="chart-card" bind:this={containerEl}>
	<div class="chart-card__header">
		<h3 class="chart-card__title">{$t('charts.track_map')}</h3>
		{#if colorMode === 'energy'}
			<InferredBadge />
		{/if}
	</div>

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
				<!-- Track outline shadow for depth -->
				{#each segments as seg}
					<line
						x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2}
						stroke="rgba(0,0,0,0.4)"
						stroke-width={TRACK_WIDTH + 3}
						stroke-linecap="round"
						style="pointer-events: none;"
					/>
				{/each}

				<!-- Track segments -->
				{#each segments as seg}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<line
						x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2}
						stroke={seg.color}
						stroke-width={hoverIdx === seg.idx ? TRACK_WIDTH_HOVER : TRACK_WIDTH}
						stroke-linecap="round"
						style="cursor: crosshair;"
						onmouseenter={() => handleSegmentHover(seg.idx)}
					/>
				{/each}

				<!-- Corner connector lines -->
				{#each cornerLabels as c}
					<line
						x1={c.trackX} y1={c.trackY}
						x2={c.labelX} y2={c.labelY}
						stroke="var(--text-muted)"
						stroke-width="0.5"
						stroke-dasharray="2,2"
						opacity="0.5"
						style="pointer-events: none;"
					/>
				{/each}

				<!-- Corner label circles (offset from track) -->
				{#each cornerLabels as c}
					<circle cx={c.labelX} cy={c.labelY} r="10" fill="var(--bg-secondary)" stroke="var(--border)" stroke-width="1" />
					<text x={c.labelX} y={c.labelY} fill="var(--text-secondary)" font-size="9" font-weight="600" text-anchor="middle" dominant-baseline="central" font-family="var(--font-mono)">
						{c.label}
					</text>
				{/each}

				<!-- Start/finish marker -->
				{#if startPos}
					<circle cx={startPos.x} cy={startPos.y} r="8" fill="none" stroke="var(--accent)" stroke-width="2.5" />
					<circle cx={startPos.x} cy={startPos.y} r="3" fill="var(--accent)" />
					<text
						x={startPos.x} y={startPos.y - 14}
						fill="var(--accent)"
						font-size="10"
						font-weight="700"
						text-anchor="middle"
						font-family="var(--font-mono)"
						style="pointer-events: none;"
					>S/F</text>
				{/if}

				<!-- Hover indicator dot -->
				{#if hoverPos}
					<circle cx={hoverPos.x} cy={hoverPos.y} r="6" fill="white" stroke="var(--text-primary)" stroke-width="2" style="pointer-events: none;" />
				{/if}
			</svg>

			<!-- Hover tooltip -->
			{#if hoverSample}
				<div class="track-map__tooltip">
					<div class="track-map__tooltip-row">
						<span class="track-map__tooltip-label">{$t('charts.speed')}</span>
						<span class="track-map__tooltip-value">{hoverSample.speed?.toFixed(0)} km/h</span>
					</div>
					<div class="track-map__tooltip-row">
						<span class="track-map__tooltip-label">{$t('charts.gear')}</span>
						<span class="track-map__tooltip-value">{hoverSample.gear}</span>
					</div>
					<div class="track-map__tooltip-row">
						<span class="track-map__tooltip-label">{$t('charts.throttle')}</span>
						<span class="track-map__tooltip-value">{hoverSample.throttle?.toFixed(0)}%</span>
					</div>
					<div class="track-map__tooltip-row">
						<span class="track-map__tooltip-label">{$t('charts.brake')}</span>
						<span class="track-map__tooltip-value {hoverSample.brake ? 'brake-active' : ''}">{hoverSample.brake ? $t('charts.brake_on') : '-'}</span>
					</div>
					{#if hoverSample.energy}
						<div class="track-map__tooltip-row">
							<span class="track-map__tooltip-label">{$t('charts.energy_state')}</span>
							<span class="track-map__tooltip-value">{hoverSample.energy}</span>
						</div>
					{/if}
					{#if hoverSample.dist != null}
						<div class="track-map__tooltip-row track-map__tooltip-dist">
							<span>{hoverSample.dist.toFixed(0)}m / {circuit?.track_length || '?'}m</span>
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Color legend -->
		{#if colorMode === 'speed'}
			<div class="track-map__legend">
				<span class="track-map__legend-label">{speedRange.min.toFixed(0)}</span>
				<div class="track-map__gradient-wrap">
					<div class="track-map__gradient-turbo"></div>
					<div class="track-map__gradient-ticks">
						{#each speedTicks as tick}
							{@const pct = ((tick - speedRange.min) / (speedRange.max - speedRange.min)) * 100}
							<span class="track-map__gradient-tick" style="left: {pct}%">{tick}</span>
						{/each}
					</div>
				</div>
				<span class="track-map__legend-label">{speedRange.max.toFixed(0)} km/h</span>
			</div>
		{:else}
			<div class="track-map__legend">
				<span class="track-map__legend-chip" style="background:{ENERGY_COLORS.deploy}">Deploy</span>
				<span class="track-map__legend-chip" style="background:{ENERGY_COLORS.harvest}">Harvest</span>
				<span class="track-map__legend-chip" style="background:{ENERGY_COLORS.clip}">Clip</span>
				<span class="track-map__legend-chip" style="background:{ENERGY_COLORS.neutral}">Neutral</span>
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
		height: 400px;
		font-family: var(--font-mono);
		color: var(--text-muted);
	}
	.track-map__container {
		position: relative;
		display: flex;
		justify-content: center;
	}
	.track-map__svg {
		width: 100%;
		max-height: 600px;
	}

	/* Tooltip */
	.track-map__tooltip {
		position: absolute;
		top: 12px;
		right: 12px;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: 10px 14px;
		font-family: var(--font-mono);
		font-size: 13px;
		color: var(--text-primary);
		line-height: 1.8;
		pointer-events: none;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
		min-width: 160px;
	}
	.track-map__tooltip-row {
		display: flex;
		justify-content: space-between;
		gap: 16px;
	}
	.track-map__tooltip-label {
		color: var(--text-muted);
	}
	.track-map__tooltip-value {
		font-weight: 600;
		color: var(--text-primary);
	}
	.track-map__tooltip-value.brake-active {
		color: var(--accent);
	}
	.track-map__tooltip-dist {
		border-top: 1px solid var(--border);
		margin-top: 4px;
		padding-top: 4px;
		justify-content: center;
	}
	.track-map__tooltip-dist span {
		color: var(--text-muted);
		font-size: 11px;
	}

	/* Legend */
	.track-map__legend {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		margin-top: var(--space-md);
		justify-content: center;
		padding: 8px 0;
	}
	.track-map__legend-label {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-muted);
		white-space: nowrap;
	}
	.track-map__gradient-wrap {
		position: relative;
		width: 200px;
	}
	.track-map__gradient-turbo {
		width: 100%;
		height: 10px;
		border-radius: 5px;
		background: linear-gradient(to right,
			#30123b, #4662d7, #36aaf9, #1ae4b6,
			#72fe5e, #c8ef34, #faba39, #f66b19,
			#ca2a04, #7a0403
		);
	}
	.track-map__gradient-ticks {
		position: relative;
		height: 16px;
	}
	.track-map__gradient-tick {
		position: absolute;
		top: 2px;
		transform: translateX(-50%);
		font-family: var(--font-mono);
		font-size: 9px;
		color: var(--text-muted);
	}
	.track-map__legend-chip {
		display: inline-block;
		padding: 3px 10px;
		border-radius: 4px;
		font-family: var(--font-mono);
		font-size: 11px;
		color: #fff;
		font-weight: 600;
	}
</style>