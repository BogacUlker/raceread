<!--
	Track Map - circuit visualization with telemetry coloring.
	Modes: single driver (speed/energy) or two-driver comparison.
	Dark track outline as base, animated lap replay, hover tooltips.
-->
<script>
	import { onMount } from 'svelte';
	import { t } from '$lib/i18n/index.js';
	import { scaleLinear, scaleDiverging } from 'd3-scale';
	import { interpolateTurbo, interpolateRdYlGn } from 'd3-scale-chromatic';
	import { ENERGY_COLORS, TEAM_COLORS } from '$lib/constants.js';
	import InferredBadge from '$lib/components/ui/InferredBadge.svelte';

	let {
		raceId,
		drivers = [],
		circuit = null,
		totalLaps = 58,
	} = $props();

	let containerEl = $state(null);
	let containerWidth = $state(500);

	// Selection state
	let driver1 = $state('');
	let driver2 = $state('');
	let selectedLap = $state(5);
	let colorMode = $state('speed'); // 'speed' | 'energy' | 'compare'
	let compareView = $state('race'); // 'race' (dots only) | 'trace' (colored lines)
	let loading = $state(false);
	let hoverIdx = $state(null);
	let hoverDriver = $state(null); // which driver's trace is hovered in compare mode

	// Telemetry data
	let telemetry1 = $state(null);
	let telemetry2 = $state(null);

	// Animation state
	let animating = $state(false);
	let animProgress = $state(0); // 0..1
	let animSpeed = $state(1); // 1x, 2x, 4x
	let animFrame = $state(null);
	let animStartTime = $state(null);

	const TRACK_WIDTH = 7;
	const TRACK_WIDTH_HOVER = 10;
	const OUTLINE_WIDTH = 12;
	const CORNER_OFFSET = 24;
	const ANIM_LAP_DURATION = 8000; // ms for 1x speed

	let availableLaps = $derived(Array.from({ length: totalLaps }, (_, i) => i + 1));
	let isCompare = $derived(colorMode === 'compare');
	let isRaceView = $derived(isCompare && compareView === 'race');
	let showTraces = $derived(!isCompare || compareView === 'trace');

	// Auto-select first two drivers
	$effect(() => {
		if (drivers.length > 0 && !driver1) {
			driver1 = drivers[0].driver;
		}
		if (drivers.length > 1 && !driver2) {
			driver2 = drivers[1].driver;
		}
	});

	// Load telemetry when selection changes
	$effect(() => {
		if (driver1 && selectedLap && raceId) {
			loadTelemetry(driver1, 1);
		}
	});

	$effect(() => {
		if (isCompare && driver2 && selectedLap && raceId) {
			loadTelemetry(driver2, 2);
		}
	});

	function getApiBase() {
		return import.meta.env.VITE_API_URL || 'http://localhost:8000';
	}

	async function loadTelemetry(driver, slot) {
		loading = true;
		try {
			const res = await fetch(`${getApiBase()}/api/races/${raceId}/telemetry?driver=${driver}&lap=${selectedLap}`);
			if (res.ok) {
				const data = await res.json();
				if (slot === 1) telemetry1 = data;
				else telemetry2 = data;
			}
		} catch { /* ignore */ }
		loading = false;
	}

	let samples1 = $derived(telemetry1?.laps?.[0]?.samples || []);
	let samples2 = $derived(telemetry2?.laps?.[0]?.samples || []);
	let team1 = $derived(drivers.find(d => d.driver === driver1)?.team || '');
	let team2 = $derived(drivers.find(d => d.driver === driver2)?.team || '');
	let color1 = $derived(TEAM_COLORS[team1] || '#00D7B6');
	let color2 = $derived(TEAM_COLORS[team2] || '#E24B4A');

	// Primary samples for bounds/scales
	let primarySamples = $derived(samples1.length > 0 ? samples1 : []);

	// Circuit outline points for background track
	let outlinePoints = $derived(circuit?.outline || []);

	// Compute bounds from outline + samples
	let bounds = $derived.by(() => {
		const allPoints = [...outlinePoints, ...primarySamples];
		if (isCompare && samples2.length) allPoints.push(...samples2);
		if (!allPoints.length) return { minX: 0, maxX: 1, minY: 0, maxY: 1 };
		let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
		for (const p of allPoints) {
			if (p.x != null && p.y != null) {
				minX = Math.min(minX, p.x);
				maxX = Math.max(maxX, p.x);
				minY = Math.min(minY, p.y);
				maxY = Math.max(maxY, p.y);
			}
		}
		const padX = (maxX - minX) * 0.10;
		const padY = (maxY - minY) * 0.10;
		return { minX: minX - padX, maxX: maxX + padX, minY: minY - padY, maxY: maxY + padY };
	});

	let trackCenter = $derived.by(() => {
		const points = outlinePoints.length > 0 ? outlinePoints : primarySamples;
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

	let xScale = $derived(scaleLinear().domain([bounds.minX, bounds.maxX]).range([50, svgWidth - 50]));
	let yScale = $derived(scaleLinear().domain([bounds.minY, bounds.maxY]).range([svgHeight - 50, 50]));

	// Speed scale for turbo colormap
	let speedRange = $derived.by(() => {
		const speeds = primarySamples.map(s => s.speed || 0).filter(s => s > 0);
		if (!speeds.length) return { min: 0, max: 350 };
		return { min: Math.min(...speeds), max: Math.max(...speeds) };
	});

	let speedScale = $derived(scaleLinear().domain([speedRange.min, speedRange.max]).range([0.05, 0.95]));

	function getSegmentColor(sample) {
		if (colorMode === 'energy') {
			const map = { D: ENERGY_COLORS.deploy, H: ENERGY_COLORS.harvest, C: ENERGY_COLORS.clip, N: ENERGY_COLORS.neutral };
			return map[sample.energy] || ENERGY_COLORS.neutral;
		}
		const val = speedScale(sample.speed || 0);
		return interpolateTurbo(val);
	}

	// Background outline path
	let outlinePath = $derived.by(() => {
		if (!outlinePoints.length) return '';
		const xs = xScale;
		const ys = yScale;
		let d = '';
		for (let i = 0; i < outlinePoints.length; i++) {
			const p = outlinePoints[i];
			if (p.x == null || p.y == null) continue;
			d += (i === 0 ? 'M' : 'L') + `${xs(p.x).toFixed(1)},${ys(p.y).toFixed(1)}`;
		}
		return d + 'Z';
	});

	// Build line segments for a set of samples
	function buildSegments(samples, colorFn) {
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
				color: colorFn(s1),
				idx: i,
			});
		}
		return segs;
	}

	let segments1 = $derived(buildSegments(primarySamples, isCompare ? () => color1 : getSegmentColor));

	let segments2 = $derived.by(() => {
		if (!isCompare || samples2.length < 2) return [];
		return buildSegments(samples2, () => color2);
	});

	// Delta segments for trace compare: single line colored by speed difference
	let deltaMax = $derived.by(() => {
		if (!isCompare || !primarySamples.length || !samples2.length) return 30;
		let maxDiff = 0;
		const len = Math.min(primarySamples.length, samples2.length);
		for (let i = 0; i < len; i++) {
			const diff = Math.abs((primarySamples[i].speed || 0) - (samples2[i].speed || 0));
			if (diff > maxDiff) maxDiff = diff;
		}
		return Math.max(maxDiff, 5);
	});

	let deltaColorScale = $derived(
		scaleDiverging(interpolateRdYlGn).domain([-deltaMax, 0, deltaMax])
	);

	let deltaSegments = $derived.by(() => {
		if (!isCompare || compareView !== 'trace' || primarySamples.length < 2 || samples2.length < 2) return [];
		const xs = xScale;
		const ys = yScale;
		const segs = [];
		const len = Math.min(primarySamples.length - 1, samples2.length - 1);
		for (let i = 0; i < len; i++) {
			const s1 = primarySamples[i];
			const s1next = primarySamples[i + 1];
			const s2 = samples2[i];
			if (s1.x == null || s1.y == null || s1next.x == null || s1next.y == null) continue;
			const delta = (s1.speed || 0) - (s2.speed || 0);
			segs.push({
				x1: xs(s1.x), y1: ys(s1.y),
				x2: xs(s1next.x), y2: ys(s1next.y),
				color: deltaColorScale(delta),
				delta,
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
		const cx = xs(trackCenter.x);
		const cy = ys(trackCenter.y);
		return circuit.corners.map(c => {
			const px = xs(c.x);
			const py = ys(c.y);
			const dx = px - cx;
			const dy = py - cy;
			const len = Math.sqrt(dx * dx + dy * dy) || 1;
			return {
				trackX: px, trackY: py,
				labelX: px + (dx / len) * CORNER_OFFSET,
				labelY: py + (dy / len) * CORNER_OFFSET,
				label: `${c.number}`,
			};
		});
	});

	// Start/finish
	let startPos = $derived.by(() => {
		if (!primarySamples.length || primarySamples[0].x == null) return null;
		return { x: xScale(primarySamples[0].x), y: yScale(primarySamples[0].y) };
	});

	// Hover
	let hoverPos = $derived.by(() => {
		if (hoverIdx === null) return null;
		const s = (hoverDriver === 2 ? samples2 : primarySamples);
		const sample = s[hoverIdx];
		if (!sample || sample.x == null || sample.y == null) return null;
		return { x: xScale(sample.x), y: yScale(sample.y) };
	});

	let hoverSample = $derived.by(() => {
		if (hoverIdx === null) return null;
		const s = (hoverDriver === 2 ? samples2 : primarySamples);
		return s[hoverIdx] || null;
	});

	// For delta trace hover: both samples at the hovered index
	let hoverSample2 = $derived.by(() => {
		if (hoverIdx === null || !isCompare) return null;
		return samples2[hoverIdx] || null;
	});

	let hoverDelta = $derived.by(() => {
		if (!hoverSample || !hoverSample2) return null;
		return (hoverSample.speed || 0) - (hoverSample2.speed || 0);
	});

	let hoverLabel = $derived(hoverDriver === 2 ? driver2 : driver1);
	let hoverColor = $derived(hoverDriver === 2 ? color2 : color1);

	// Active sample: animation takes priority over hover (nearest sample for data display)
	function nearestSample(samples, progress) {
		if (!samples.length) return null;
		return samples[Math.min(Math.round(progress * (samples.length - 1)), samples.length - 1)];
	}
	let animSample1 = $derived(animProgress > 0 && primarySamples.length ? nearestSample(primarySamples, animProgress) : null);
	let animSample2 = $derived(animProgress > 0 && isCompare && samples2.length ? nearestSample(samples2, animProgress) : null);
	let showAnimTooltip = $derived(animProgress > 0 && animSample1 != null);

	// Speed delta for compare tooltip
	let speedDelta = $derived.by(() => {
		if (!animSample1 || !animSample2) return null;
		const s1 = animSample1.speed ?? 0;
		const s2 = animSample2.speed ?? 0;
		return s1 - s2;
	});

	function handleSegmentHover(idx, driverSlot) {
		hoverIdx = idx;
		hoverDriver = driverSlot;
	}

	// Speed legend ticks
	let speedTicks = $derived.by(() => {
		const { min, max } = speedRange;
		const step = 50;
		const ticks = [];
		const start = Math.ceil(min / step) * step;
		for (let v = start; v <= max; v += step) ticks.push(v);
		return ticks;
	});

	// ───── Animation ─────

	// Interpolate position between two samples for smooth movement
	function lerpPos(samples, progress) {
		if (!samples.length) return null;
		const t = progress * (samples.length - 1);
		const i = Math.floor(t);
		const frac = t - i;
		const s1 = samples[Math.min(i, samples.length - 1)];
		const s2 = samples[Math.min(i + 1, samples.length - 1)];
		if (!s1 || s1.x == null || !s2 || s2.x == null) return null;
		const x = s1.x + (s2.x - s1.x) * frac;
		const y = s1.y + (s2.y - s1.y) * frac;
		return { x: xScale(x), y: yScale(y) };
	}

	let animPos1 = $derived.by(() => {
		if (animProgress === 0 || !primarySamples.length) return null;
		return lerpPos(primarySamples, animProgress);
	});

	let animPos2 = $derived.by(() => {
		if (animProgress === 0 || !isCompare || !samples2.length) return null;
		return lerpPos(samples2, animProgress);
	});

	let scrubbing = $state(false);

	function startAnimation() {
		animProgress = 0;
		animating = true;
		animStartTime = performance.now();
		animLoop();
	}

	function resumeAnimation() {
		animating = true;
		animStartTime = performance.now() - (animProgress * ANIM_LAP_DURATION / animSpeed);
		animLoop();
	}

	function stopAnimation() {
		animating = false;
		if (animFrame) cancelAnimationFrame(animFrame);
		animFrame = null;
	}

	function toggleAnimation() {
		if (animating) {
			stopAnimation();
		} else if (animProgress >= 1) {
			startAnimation();
		} else {
			resumeAnimation();
		}
	}

	function animLoop() {
		if (!animating || scrubbing) return;
		const elapsed = performance.now() - animStartTime;
		const duration = ANIM_LAP_DURATION / animSpeed;
		animProgress = Math.min(elapsed / duration, 1);
		if (animProgress >= 1) {
			animating = false;
			animProgress = 1;
			return;
		}
		animFrame = requestAnimationFrame(animLoop);
	}

	function handleScrubStart() {
		scrubbing = true;
		if (animating) {
			if (animFrame) cancelAnimationFrame(animFrame);
			animFrame = null;
		}
	}

	function handleScrubInput(e) {
		animProgress = +e.target.value / 1000;
	}

	function handleScrubEnd() {
		scrubbing = false;
		if (animating) {
			animStartTime = performance.now() - (animProgress * ANIM_LAP_DURATION / animSpeed);
			animLoop();
		}
	}

	function cycleSpeed() {
		const speeds = [1, 2, 4];
		const idx = speeds.indexOf(animSpeed);
		animSpeed = speeds[(idx + 1) % speeds.length];
		if (animating) {
			animStartTime = performance.now() - (animProgress * ANIM_LAP_DURATION / animSpeed);
		}
	}

	onMount(() => {
		if (!containerEl) return;
		const ro = new ResizeObserver((entries) => {
			for (const entry of entries) containerWidth = entry.contentRect.width;
		});
		ro.observe(containerEl);
		return () => {
			ro.disconnect();
			stopAnimation();
		};
	});
</script>

<div class="chart-card" bind:this={containerEl}>
	<div class="chart-card__header">
		<h3 class="chart-card__title">{$t('charts.track_map')}</h3>
		{#if colorMode === 'energy'}
			<InferredBadge />
		{/if}
	</div>

	<!-- Controls row -->
	<div class="track-map__controls">
		<select bind:value={driver1} class="track-map__select">
			{#each drivers as d}
				<option value={d.driver}>{d.driver}</option>
			{/each}
		</select>

		{#if isCompare}
			<span class="track-map__vs">vs</span>
			<select bind:value={driver2} class="track-map__select">
				{#each drivers as d}
					<option value={d.driver}>{d.driver}</option>
				{/each}
			</select>
		{/if}

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
			<button class="track-map__mode-btn" class:active={colorMode === 'compare'} onclick={() => colorMode = 'compare'}>
				{$t('charts.compare')}
			</button>
		</div>
		{#if isCompare}
			<div class="track-map__sub-toggle">
				<button class="track-map__sub-btn" class:active={compareView === 'race'} onclick={() => compareView = 'race'}>
					Race
				</button>
				<button class="track-map__sub-btn" class:active={compareView === 'trace'} onclick={() => compareView = 'trace'}>
					Trace
				</button>
			</div>
		{/if}
	</div>

	{#if loading}
		<div class="track-map__loading">{$t('common.loading')}</div>
	{:else if primarySamples.length === 0}
		<div class="track-map__loading">{$t('common.no_data')}</div>
	{:else}
		<div class="track-map__container">
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<svg viewBox="0 0 {svgWidth} {svgHeight}" class="track-map__svg" onmouseleave={() => { hoverIdx = null; hoverDriver = null; }}>

				<!-- Track outline background - brighter in race view -->
				{#if outlinePath}
					<path
						d={outlinePath}
						fill="none"
						stroke={isRaceView ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.06)'}
						stroke-width={isRaceView ? OUTLINE_WIDTH + 4 : OUTLINE_WIDTH}
						stroke-linejoin="round"
						stroke-linecap="round"
						style="pointer-events: none;"
					/>
				{/if}

				{#if showTraces}
					{#if isCompare && deltaSegments.length > 0}
						<!-- Compare trace: delta heatmap (single line) -->
						{#each deltaSegments as seg}
							<line
								x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2}
								stroke="rgba(0,0,0,0.35)"
								stroke-width={TRACK_WIDTH + 3}
								stroke-linecap="round"
								style="pointer-events: none;"
							/>
						{/each}
						{#each deltaSegments as seg}
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<line
								x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2}
								stroke={seg.color}
								stroke-width={hoverIdx === seg.idx ? TRACK_WIDTH_HOVER : TRACK_WIDTH}
								stroke-linecap="round"
								style="cursor: crosshair;"
								onmouseenter={() => handleSegmentHover(seg.idx, 1)}
							/>
						{/each}
					{:else}
						<!-- Single driver: speed or energy coloring -->
						{#each segments1 as seg}
							<line
								x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2}
								stroke="rgba(0,0,0,0.35)"
								stroke-width={TRACK_WIDTH + 3}
								stroke-linecap="round"
								style="pointer-events: none;"
							/>
						{/each}
						{#each segments1 as seg}
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<line
								x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2}
								stroke={seg.color}
								stroke-width={hoverIdx === seg.idx ? TRACK_WIDTH_HOVER : TRACK_WIDTH}
								stroke-linecap="round"
								style="cursor: crosshair;"
								onmouseenter={() => handleSegmentHover(seg.idx, 1)}
							/>
						{/each}
					{/if}
				{/if}

				<!-- Corner connector lines -->
				{#each cornerLabels as c}
					<line
						x1={c.trackX} y1={c.trackY} x2={c.labelX} y2={c.labelY}
						stroke="var(--text-muted)" stroke-width="0.5" stroke-dasharray="2,2" opacity="0.4"
						style="pointer-events: none;"
					/>
				{/each}

				<!-- Corner labels -->
				{#each cornerLabels as c}
					<circle cx={c.labelX} cy={c.labelY} r="10" fill="var(--bg-secondary)" stroke="var(--border)" stroke-width="1" opacity="0.9" />
					<text x={c.labelX} y={c.labelY} fill="var(--text-secondary)" font-size="9" font-weight="600"
						text-anchor="middle" dominant-baseline="central" font-family="var(--font-mono)">
						{c.label}
					</text>
				{/each}

				<!-- Start/finish marker -->
				{#if startPos}
					<circle cx={startPos.x} cy={startPos.y} r="8" fill="none" stroke="var(--accent)" stroke-width="2.5" />
					<circle cx={startPos.x} cy={startPos.y} r="3" fill="var(--accent)" />
					<text x={startPos.x} y={startPos.y - 14} fill="var(--accent)" font-size="10" font-weight="700"
						text-anchor="middle" font-family="var(--font-mono)" style="pointer-events: none;">S/F</text>
				{/if}

				<!-- Animated driver dots -->
				{#if animating || animProgress > 0}
					{@const dotR = isRaceView ? 10 : 8}
					{@const strokeW = isRaceView ? 3 : 2.5}
					{#if animPos1}
						{#if isRaceView}
							<circle cx={animPos1.x} cy={animPos1.y} r={dotR + 6}
								fill={color1} fill-opacity="0.15"
								style="pointer-events: none;"
							/>
						{/if}
						<circle cx={animPos1.x} cy={animPos1.y} r={dotR}
							fill={isCompare ? color1 : 'var(--accent)'}
							stroke="white" stroke-width={strokeW}
							style="pointer-events: none; filter: drop-shadow(0 0 6px rgba(0,0,0,0.7));"
						/>
						{#if isCompare}
							<text x={animPos1.x} y={animPos1.y - dotR - 6} fill={color1} font-size={isRaceView ? '12' : '10'} font-weight="700"
								text-anchor="middle" font-family="var(--font-mono)" style="pointer-events: none; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.8));">{driver1}</text>
						{/if}
					{/if}
					{#if animPos2}
						{#if isRaceView}
							<circle cx={animPos2.x} cy={animPos2.y} r={dotR + 6}
								fill={color2} fill-opacity="0.15"
								style="pointer-events: none;"
							/>
						{/if}
						<circle cx={animPos2.x} cy={animPos2.y} r={dotR}
							fill={color2}
							stroke="white" stroke-width={strokeW}
							style="pointer-events: none; filter: drop-shadow(0 0 6px rgba(0,0,0,0.7));"
						/>
						<text x={animPos2.x} y={animPos2.y - dotR - 6} fill={color2} font-size={isRaceView ? '12' : '10'} font-weight="700"
							text-anchor="middle" font-family="var(--font-mono)" style="pointer-events: none; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.8));">{driver2}</text>
					{/if}
				{/if}

				<!-- Hover indicator dot (only when not animating) -->
				{#if hoverPos && !animating}
					<circle cx={hoverPos.x} cy={hoverPos.y} r="6"
						fill={isCompare ? hoverColor : 'white'}
						stroke={isCompare ? 'white' : 'var(--text-primary)'}
						stroke-width="2" style="pointer-events: none;" />
				{/if}
			</svg>

			<!-- Telemetry info panel -->
			{#if showAnimTooltip}
				<div class="track-map__tooltip">
					{#if isCompare && animSample1 && animSample2}
						<!-- Compare mode: two columns -->
						<div class="track-map__tooltip-compare-header">
							<span style="color: {color1}; font-weight: 700;">{driver1}</span>
							<span class="track-map__tooltip-vs">vs</span>
							<span style="color: {color2}; font-weight: 700;">{driver2}</span>
						</div>
						<div class="track-map__tooltip-compare">
							<div class="track-map__tooltip-col">
								<div class="track-map__tooltip-val">{animSample1.speed?.toFixed(0)} <small>km/h</small></div>
								<div class="track-map__tooltip-val">{animSample1.gear}</div>
								<div class="track-map__tooltip-val">{animSample1.throttle?.toFixed(0)}%</div>
								<div class="track-map__tooltip-val {animSample1.brake ? 'brake-active' : ''}">{animSample1.brake ? $t('charts.brake_on') : '-'}</div>
								<div class="track-map__tooltip-val">{animSample1.energy || '-'}</div>
							</div>
							<div class="track-map__tooltip-labels">
								<div>{$t('charts.speed')}</div>
								<div>{$t('charts.gear')}</div>
								<div>{$t('charts.throttle')}</div>
								<div>{$t('charts.brake')}</div>
								<div>{$t('charts.energy_state')}</div>
							</div>
							<div class="track-map__tooltip-col">
								<div class="track-map__tooltip-val">{animSample2.speed?.toFixed(0)} <small>km/h</small></div>
								<div class="track-map__tooltip-val">{animSample2.gear}</div>
								<div class="track-map__tooltip-val">{animSample2.throttle?.toFixed(0)}%</div>
								<div class="track-map__tooltip-val {animSample2.brake ? 'brake-active' : ''}">{animSample2.brake ? $t('charts.brake_on') : '-'}</div>
								<div class="track-map__tooltip-val">{animSample2.energy || '-'}</div>
							</div>
						</div>
						{#if speedDelta != null}
							<div class="track-map__tooltip-delta" class:delta-pos={speedDelta > 0} class:delta-neg={speedDelta < 0}>
								{speedDelta > 0 ? '+' : ''}{speedDelta.toFixed(0)} km/h
							</div>
						{/if}
						{#if animSample1.dist != null}
							<div class="track-map__tooltip-row track-map__tooltip-dist">
								<span>{animSample1.dist.toFixed(0)}m / {circuit?.track_length || '?'}m</span>
							</div>
						{/if}
					{:else if animSample1}
						<!-- Single driver -->
						<div class="track-map__tooltip-row">
							<span class="track-map__tooltip-label">{$t('charts.speed')}</span>
							<span class="track-map__tooltip-value">{animSample1.speed?.toFixed(0)} km/h</span>
						</div>
						<div class="track-map__tooltip-row">
							<span class="track-map__tooltip-label">{$t('charts.gear')}</span>
							<span class="track-map__tooltip-value">{animSample1.gear}</span>
						</div>
						<div class="track-map__tooltip-row">
							<span class="track-map__tooltip-label">{$t('charts.throttle')}</span>
							<span class="track-map__tooltip-value">{animSample1.throttle?.toFixed(0)}%</span>
						</div>
						<div class="track-map__tooltip-row">
							<span class="track-map__tooltip-label">{$t('charts.brake')}</span>
							<span class="track-map__tooltip-value {animSample1.brake ? 'brake-active' : ''}">{animSample1.brake ? $t('charts.brake_on') : '-'}</span>
						</div>
						{#if animSample1.energy}
							<div class="track-map__tooltip-row">
								<span class="track-map__tooltip-label">{$t('charts.energy_state')}</span>
								<span class="track-map__tooltip-value">{animSample1.energy}</span>
							</div>
						{/if}
						{#if animSample1.dist != null}
							<div class="track-map__tooltip-row track-map__tooltip-dist">
								<span>{animSample1.dist.toFixed(0)}m / {circuit?.track_length || '?'}m</span>
							</div>
						{/if}
					{/if}
				</div>
			{:else if hoverSample && !animating}
				<div class="track-map__tooltip">
					{#if isCompare && compareView === 'trace' && hoverSample2}
						<!-- Delta trace hover: both drivers -->
						<div class="track-map__tooltip-compare-header">
							<span style="color: {color1}; font-weight: 700;">{driver1}</span>
							<span class="track-map__tooltip-vs">vs</span>
							<span style="color: {color2}; font-weight: 700;">{driver2}</span>
						</div>
						<div class="track-map__tooltip-compare">
							<div class="track-map__tooltip-col">
								<div class="track-map__tooltip-val">{hoverSample.speed?.toFixed(0)} <small>km/h</small></div>
								<div class="track-map__tooltip-val">{hoverSample.gear}</div>
								<div class="track-map__tooltip-val">{hoverSample.throttle?.toFixed(0)}%</div>
								<div class="track-map__tooltip-val {hoverSample.brake ? 'brake-active' : ''}">{hoverSample.brake ? $t('charts.brake_on') : '-'}</div>
							</div>
							<div class="track-map__tooltip-labels">
								<div>{$t('charts.speed')}</div>
								<div>{$t('charts.gear')}</div>
								<div>{$t('charts.throttle')}</div>
								<div>{$t('charts.brake')}</div>
							</div>
							<div class="track-map__tooltip-col">
								<div class="track-map__tooltip-val">{hoverSample2.speed?.toFixed(0)} <small>km/h</small></div>
								<div class="track-map__tooltip-val">{hoverSample2.gear}</div>
								<div class="track-map__tooltip-val">{hoverSample2.throttle?.toFixed(0)}%</div>
								<div class="track-map__tooltip-val {hoverSample2.brake ? 'brake-active' : ''}">{hoverSample2.brake ? $t('charts.brake_on') : '-'}</div>
							</div>
						</div>
						{#if hoverDelta != null}
							<div class="track-map__tooltip-delta" class:delta-pos={hoverDelta > 0} class:delta-neg={hoverDelta < 0}>
								{hoverDelta > 0 ? '+' : ''}{hoverDelta.toFixed(0)} km/h
							</div>
						{/if}
						{#if hoverSample.dist != null}
							<div class="track-map__tooltip-row track-map__tooltip-dist">
								<span>{hoverSample.dist.toFixed(0)}m / {circuit?.track_length || '?'}m</span>
							</div>
						{/if}
					{:else}
						<!-- Single driver hover -->
						{#if isCompare}
							<div class="track-map__tooltip-driver" style="color: {hoverColor}">{hoverLabel}</div>
						{/if}
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
					{/if}
				</div>
			{/if}

			<!-- Animation speed indicator -->
			{#if animating}
				<div class="track-map__anim-info">
					{$t('tooltip.lap')} {selectedLap} - {(animProgress * 100).toFixed(0)}%
				</div>
			{/if}
		</div>

		<!-- Animation controls -->
		<div class="track-map__anim-controls">
			<button class="track-map__anim-btn" onclick={toggleAnimation}>
				{#if animating}
					<span class="anim-icon">&#10074;&#10074;</span>
				{:else}
					<span class="anim-icon">&#9654;</span>
				{/if}
			</button>
			<button class="track-map__anim-btn track-map__anim-speed" onclick={cycleSpeed}>
				{animSpeed}x
			</button>
			<input
				type="range"
				class="track-map__slider"
				min="0"
				max="1000"
				value={Math.round(animProgress * 1000)}
				oninput={handleScrubInput}
				onmousedown={handleScrubStart}
				ontouchstart={handleScrubStart}
				onmouseup={handleScrubEnd}
				ontouchend={handleScrubEnd}
			/>
			<span class="track-map__anim-time">
				{(animProgress * 100).toFixed(0)}%
			</span>
		</div>

		<!-- Legends -->
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
		{:else if colorMode === 'energy'}
			<div class="track-map__legend">
				<span class="track-map__legend-chip" style="background:{ENERGY_COLORS.deploy}">Deploy</span>
				<span class="track-map__legend-chip" style="background:{ENERGY_COLORS.harvest}">Harvest</span>
				<span class="track-map__legend-chip" style="background:{ENERGY_COLORS.clip}">Clip</span>
				<span class="track-map__legend-chip" style="background:{ENERGY_COLORS.neutral}">Neutral</span>
			</div>
		{:else if compareView === 'trace'}
			<!-- Compare trace legend: delta gradient -->
			<div class="track-map__legend">
				<span class="track-map__legend-label" style="color: {color2}">{driver2} {$t('charts.faster')}</span>
				<div class="track-map__gradient-wrap">
					<div class="track-map__gradient-delta"></div>
				</div>
				<span class="track-map__legend-label" style="color: {color1}">{driver1} {$t('charts.faster')}</span>
			</div>
		{:else}
			<!-- Compare race legend: dots -->
			<div class="track-map__legend">
				<span class="track-map__legend-driver">
					<span class="track-map__legend-dot" style="background: {color1}"></span>
					{driver1}
				</span>
				<span class="track-map__vs-legend">vs</span>
				<span class="track-map__legend-driver">
					<span class="track-map__legend-dot" style="background: {color2}"></span>
					{driver2}
				</span>
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
	.track-map__vs {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-muted);
		font-weight: 600;
	}
	.track-map__mode-toggle {
		display: flex;
		gap: 0;
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
	.track-map__mode-btn:not(:first-child) { border-left: none; }
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
	.track-map__tooltip-driver {
		font-size: 14px;
		font-weight: 700;
		margin-bottom: 4px;
		padding-bottom: 4px;
		border-bottom: 1px solid var(--border);
	}
	.track-map__tooltip-row {
		display: flex;
		justify-content: space-between;
		gap: 16px;
	}
	.track-map__tooltip-label { color: var(--text-muted); }
	.track-map__tooltip-value { font-weight: 600; color: var(--text-primary); }
	.track-map__tooltip-value.brake-active { color: var(--accent); }
	.track-map__tooltip-dist {
		border-top: 1px solid var(--border);
		margin-top: 4px;
		padding-top: 4px;
		justify-content: center;
	}
	.track-map__tooltip-dist span { color: var(--text-muted); font-size: 11px; }

	/* Compare tooltip */
	.track-map__tooltip-compare-header {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		font-family: var(--font-mono);
		font-size: 13px;
		margin-bottom: 6px;
		padding-bottom: 6px;
		border-bottom: 1px solid var(--border);
	}
	.track-map__tooltip-vs {
		font-size: 10px;
		color: var(--text-muted);
	}
	.track-map__tooltip-compare {
		display: grid;
		grid-template-columns: 1fr auto 1fr;
		gap: 4px 10px;
		align-items: center;
	}
	.track-map__tooltip-col {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.track-map__tooltip-col:first-child { text-align: right; }
	.track-map__tooltip-col:last-child { text-align: left; }
	.track-map__tooltip-labels {
		display: flex;
		flex-direction: column;
		gap: 4px;
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--text-muted);
		text-align: center;
	}
	.track-map__tooltip-val {
		font-family: var(--font-mono);
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
		white-space: nowrap;
	}
	.track-map__tooltip-val.brake-active { color: var(--accent); }
	.track-map__tooltip-val small { font-size: 10px; font-weight: 400; color: var(--text-muted); }
	.track-map__tooltip-delta {
		text-align: center;
		font-family: var(--font-mono);
		font-size: 12px;
		font-weight: 700;
		padding: 4px 0 2px;
		margin-top: 4px;
		border-top: 1px solid var(--border);
		color: var(--text-muted);
	}
	.track-map__tooltip-delta.delta-pos { color: #22C55E; }
	.track-map__tooltip-delta.delta-neg { color: #EF4444; }

	/* Sub-toggle for compare view */
	.track-map__sub-toggle {
		display: flex;
		gap: 0;
	}
	.track-map__sub-btn {
		font-family: var(--font-mono);
		font-size: 11px;
		padding: 3px 8px;
		border: 1px solid var(--border);
		background: transparent;
		color: var(--text-muted);
		cursor: pointer;
		transition: all 0.15s;
	}
	.track-map__sub-btn:first-child { border-radius: var(--radius-sm) 0 0 var(--radius-sm); }
	.track-map__sub-btn:last-child { border-radius: 0 var(--radius-sm) var(--radius-sm) 0; border-left: none; }
	.track-map__sub-btn.active {
		background: var(--bg-secondary);
		color: var(--text-primary);
		border-color: var(--text-muted);
	}

	/* Animation controls */
	.track-map__anim-controls {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-top: var(--space-sm);
		padding: 0 4px;
	}
	.track-map__anim-btn {
		font-family: var(--font-mono);
		font-size: 12px;
		width: 32px;
		height: 28px;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-secondary);
		color: var(--text-primary);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.15s;
	}
	.track-map__anim-btn:hover {
		border-color: var(--text-muted);
	}
	.track-map__anim-speed {
		width: 36px;
		font-size: 11px;
		font-weight: 600;
	}
	.anim-icon {
		font-size: 10px;
		line-height: 1;
	}
	.track-map__slider {
		flex: 1;
		-webkit-appearance: none;
		appearance: none;
		height: 6px;
		background: var(--bg-primary);
		border-radius: 3px;
		outline: none;
		cursor: pointer;
	}
	.track-map__slider::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 14px;
		height: 14px;
		border-radius: 50%;
		background: var(--accent);
		border: 2px solid var(--bg-card);
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
		cursor: grab;
		transition: transform 0.1s;
	}
	.track-map__slider::-webkit-slider-thumb:active {
		cursor: grabbing;
		transform: scale(1.2);
	}
	.track-map__slider::-moz-range-thumb {
		width: 14px;
		height: 14px;
		border-radius: 50%;
		background: var(--accent);
		border: 2px solid var(--bg-card);
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
		cursor: grab;
	}
	.track-map__slider::-moz-range-track {
		height: 6px;
		background: var(--bg-primary);
		border-radius: 3px;
	}
	.track-map__anim-time {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-muted);
		min-width: 32px;
		text-align: right;
	}
	.track-map__anim-info {
		position: absolute;
		top: 12px;
		left: 12px;
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-muted);
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 4px 8px;
		pointer-events: none;
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
	.track-map__gradient-wrap { position: relative; width: 200px; }
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
	.track-map__gradient-delta {
		width: 100%;
		height: 10px;
		border-radius: 5px;
		background: linear-gradient(to right,
			#a50026, #d73027, #f46d43, #fdae61,
			#ffffbf,
			#a6d96a, #66bd63, #1a9850, #006837
		);
	}
	.track-map__gradient-ticks { position: relative; height: 16px; }
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

	/* Compare legend */
	.track-map__legend-driver {
		display: flex;
		align-items: center;
		gap: 6px;
		font-family: var(--font-mono);
		font-size: 12px;
		font-weight: 600;
		color: var(--text-primary);
	}
	.track-map__legend-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		border: 2px solid rgba(255,255,255,0.5);
		flex-shrink: 0;
	}
	.track-map__vs-legend {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-muted);
	}

	@media (max-width: 768px) {
		.track-map__loading {
			height: 300px;
		}
		.track-map__svg {
			max-height: 400px;
		}
		.track-map__tooltip {
			top: 4px;
			right: 4px;
			padding: 6px 10px;
			font-size: 11px;
			min-width: 140px;
		}
	}

	@media (max-width: 480px) {
		.track-map__loading {
			height: 250px;
		}
		.track-map__svg {
			max-height: 320px;
		}
	}
</style>
