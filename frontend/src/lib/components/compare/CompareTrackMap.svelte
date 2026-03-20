<!--
	CompareTrackMap - delta heatmap track map for compare page.
	Props-only, no store deps. Animated replay with play/pause + scrubbar.
	Colors track by speed delta between two drivers.
-->
<script>
	import { onMount } from 'svelte';
	import { scaleLinear } from 'd3-scale';

	let { raceId, driver1, driver2, color1, color2, selectedLap, circuit, totalLaps } = $props();

	let containerEl = $state(null);
	let containerWidth = $state(500);
	let telemetryData = $state({});
	let loading = $state(false);

	// Animation state
	let animating = $state(false);
	let animProgress = $state(0);
	let animFrame = $state(null);
	let animStartTime = $state(null);
	let animSpeed = $state(0.25);
	const ANIM_LAP_DURATION = 8000;

	const TRACK_WIDTH = 7;
	const OUTLINE_WIDTH = 12;
	const CORNER_OFFSET = 22;

	function getApiBase() {
		return import.meta.env.VITE_API_URL || 'http://localhost:8000';
	}

	$effect(() => {
		if (driver1 && driver2 && selectedLap && raceId) {
			fetchComparison();
		}
	});

	async function fetchComparison() {
		loading = true;
		stopAnimation();
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

	let d1Samples = $derived(telemetryData[driver1]?.samples || []);
	let d2Samples = $derived(telemetryData[driver2]?.samples || []);
	let outlinePoints = $derived(circuit?.outline || []);

	// Compute bounds from outline + samples
	let bounds = $derived.by(() => {
		const allPoints = [...outlinePoints, ...d1Samples, ...d2Samples];
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
		const padX = (maxX - minX) * 0.12;
		const padY = (maxY - minY) * 0.12;
		return { minX: minX - padX, maxX: maxX + padX, minY: minY - padY, maxY: maxY + padY };
	});

	let svgWidth = $derived(Math.max(300, containerWidth));
	let svgHeight = $derived.by(() => {
		const aspect = (bounds.maxY - bounds.minY) / (bounds.maxX - bounds.minX);
		return Math.max(300, Math.min(550, svgWidth * aspect));
	});

	let xScale = $derived(scaleLinear().domain([bounds.minX, bounds.maxX]).range([50, svgWidth - 50]));
	let yScale = $derived(scaleLinear().domain([bounds.minY, bounds.maxY]).range([svgHeight - 50, 50]));

	// Background outline path
	let outlinePath = $derived.by(() => {
		if (!outlinePoints.length) return '';
		let d = '';
		for (let i = 0; i < outlinePoints.length; i++) {
			const p = outlinePoints[i];
			if (p.x == null || p.y == null) continue;
			d += (i === 0 ? 'M' : 'L') + `${xScale(p.x).toFixed(1)},${yScale(p.y).toFixed(1)}`;
		}
		return d + 'Z';
	});

	// Delta colored segments: d1 faster = color1, d2 faster = color2
	let deltaSegments = $derived.by(() => {
		if (d1Samples.length < 2 || d2Samples.length < 2) return [];
		const segs = [];
		const len = Math.min(d1Samples.length - 1, d2Samples.length - 1);
		for (let i = 0; i < len; i++) {
			const s1 = d1Samples[i];
			const s1next = d1Samples[i + 1];
			if (s1.x == null || s1.y == null || s1next.x == null || s1next.y == null) continue;
			const speedDelta = (s1.speed || 0) - (d2Samples[i]?.speed || 0);
			segs.push({
				x1: xScale(s1.x), y1: yScale(s1.y),
				x2: xScale(s1next.x), y2: yScale(s1next.y),
				color: speedDelta >= 0 ? color1 : color2,
				opacity: Math.min(1, Math.abs(speedDelta) / 40 + 0.3),
				idx: i,
			});
		}
		return segs;
	});

	// Track center for corner label offset
	let trackCenter = $derived.by(() => {
		const pts = outlinePoints.length > 0 ? outlinePoints : d1Samples;
		if (!pts.length) return { x: 0, y: 0 };
		let sx = 0, sy = 0, n = 0;
		for (const p of pts) {
			if (p.x != null && p.y != null) { sx += p.x; sy += p.y; n++; }
		}
		return { x: sx / n, y: sy / n };
	});

	// Corner labels
	let cornerLabels = $derived.by(() => {
		if (!circuit?.corners) return [];
		const cx = xScale(trackCenter.x);
		const cy = yScale(trackCenter.y);
		return circuit.corners.map(c => {
			const px = xScale(c.x);
			const py = yScale(c.y);
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

	// Animation dots positions
	let dot1Pos = $derived.by(() => {
		if (!d1Samples.length) return null;
		const idx = Math.min(Math.floor(animProgress * (d1Samples.length - 1)), d1Samples.length - 1);
		const s = d1Samples[idx];
		if (s?.x == null || s?.y == null) return null;
		return { x: xScale(s.x), y: yScale(s.y) };
	});

	let dot2Pos = $derived.by(() => {
		if (!d2Samples.length) return null;
		const idx = Math.min(Math.floor(animProgress * (d2Samples.length - 1)), d2Samples.length - 1);
		const s = d2Samples[idx];
		if (s?.x == null || s?.y == null) return null;
		return { x: xScale(s.x), y: yScale(s.y) };
	});

	function startAnimation() {
		animating = true;
		animStartTime = performance.now() - (animProgress * ANIM_LAP_DURATION / animSpeed);
		tick();
	}

	function stopAnimation() {
		animating = false;
		if (animFrame) {
			cancelAnimationFrame(animFrame);
			animFrame = null;
		}
	}

	function toggleAnimation() {
		if (animating) {
			stopAnimation();
		} else {
			if (animProgress >= 0.99) animProgress = 0;
			startAnimation();
		}
	}

	function tick() {
		if (!animating) return;
		const elapsed = (performance.now() - animStartTime) * animSpeed;
		animProgress = Math.min(elapsed / ANIM_LAP_DURATION, 1);
		if (animProgress >= 1) {
			animating = false;
			animProgress = 1;
			return;
		}
		animFrame = requestAnimationFrame(tick);
	}

	function handleScrub(e) {
		const val = parseFloat(e.target.value);
		animProgress = val;
		if (animating) {
			animStartTime = performance.now() - (val * ANIM_LAP_DURATION / animSpeed);
		}
	}

	// ResizeObserver
	onMount(() => {
		if (!containerEl) return;
		const ro = new ResizeObserver((entries) => {
			for (const entry of entries) {
				containerWidth = entry.contentRect.width;
			}
		});
		ro.observe(containerEl);
		return () => {
			ro.disconnect();
			stopAnimation();
		};
	});
</script>

<div class="ctm" bind:this={containerEl}>
	<div class="ctm__header">
		<h3 class="ctm__title">TRACK MAP</h3>
		<span class="ctm__lap">LAP {selectedLap}</span>
	</div>

	{#if loading}
		<div class="ctm__empty">Loading...</div>
	{:else if d1Samples.length === 0 && d2Samples.length === 0}
		<div class="ctm__empty">No telemetry data</div>
	{:else}
		<svg width={svgWidth} height={svgHeight} class="ctm__svg">
			<!-- Background outline -->
			{#if outlinePath}
				<path d={outlinePath} fill="none" stroke="#2E3240" stroke-width={OUTLINE_WIDTH} stroke-linejoin="round" stroke-linecap="round" />
			{/if}

			<!-- Delta colored segments -->
			{#each deltaSegments as seg}
				<line
					x1={seg.x1} y1={seg.y1}
					x2={seg.x2} y2={seg.y2}
					stroke={seg.color}
					stroke-width={TRACK_WIDTH}
					stroke-linecap="round"
					opacity={seg.opacity}
				/>
			{/each}

			<!-- Corner labels -->
			{#each cornerLabels as cl}
				<line x1={cl.trackX} y1={cl.trackY} x2={cl.labelX} y2={cl.labelY} stroke="#6B7280" stroke-width="0.5" stroke-opacity="0.5" />
				<text x={cl.labelX} y={cl.labelY} fill="#6B7280" font-size="10" text-anchor="middle" dominant-baseline="middle" font-family="'JetBrains Mono', monospace">{cl.label}</text>
			{/each}

			<!-- Animation dots -->
			{#if dot1Pos}
				<circle cx={dot1Pos.x} cy={dot1Pos.y} r="6" fill={color1} stroke="#0F1117" stroke-width="2" />
			{/if}
			{#if dot2Pos}
				<circle cx={dot2Pos.x} cy={dot2Pos.y} r="6" fill={color2} stroke="#0F1117" stroke-width="2" />
			{/if}

			<!-- Start/finish marker -->
			{#if d1Samples.length > 0 && d1Samples[0].x != null}
				<circle
					cx={xScale(d1Samples[0].x)}
					cy={yScale(d1Samples[0].y)}
					r="3"
					fill="none"
					stroke="#E8E8ED"
					stroke-width="1.5"
				/>
			{/if}
		</svg>

		<!-- Controls -->
		<div class="ctm__controls">
			<button class="ctm__btn" onclick={toggleAnimation}>
				{animating ? 'PAUSE' : 'PLAY'}
			</button>
			<input
				type="range"
				class="ctm__scrub"
				min="0"
				max="1"
				step="0.001"
				value={animProgress}
				oninput={handleScrub}
			/>
			<select class="ctm__speed" bind:value={animSpeed}>
				<option value={0.25}>0.25x</option>
				<option value={0.5}>0.5x</option>
				<option value={1}>1x</option>
				<option value={2}>2x</option>
			</select>
		</div>

		<!-- Legend -->
		<div class="ctm__legend">
			<span class="ctm__legend-item">
				<span class="ctm__legend-dot" style="background:{color1}"></span>
				{driver1} faster
			</span>
			<span class="ctm__legend-item">
				<span class="ctm__legend-dot" style="background:{color2}"></span>
				{driver2} faster
			</span>
		</div>
	{/if}
</div>

<style>
	.ctm {
		background: #1A1D27;
		padding: 1.25rem;
		border-left: 2px solid transparent;
		font-family: 'DM Sans', sans-serif;
		transition: border-color 0.25s, box-shadow 0.25s;
	}
	.ctm:hover {
		border-left-color: #E24B4A;
		box-shadow: -4px 0 20px -4px rgba(226, 75, 74, 0.12);
	}
	.ctm__header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0.75rem;
	}
	.ctm__title {
		font-family: 'Space Grotesk', sans-serif;
		text-transform: uppercase;
		font-size: 15px;
		font-weight: 700;
		color: #E8E8ED;
		margin: 0;
	}
	.ctm__lap {
		font-family: 'JetBrains Mono', monospace;
		font-size: 11px;
		color: #6B7280;
		letter-spacing: 0.05em;
	}
	.ctm__svg {
		display: block;
		width: 100%;
		height: auto;
	}
	.ctm__empty {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 300px;
		font-family: 'JetBrains Mono', monospace;
		font-size: 13px;
		color: #6B7280;
	}
	.ctm__controls {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-top: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid #2E3240;
	}
	.ctm__btn {
		font-family: 'JetBrains Mono', monospace;
		font-size: 11px;
		font-weight: 600;
		letter-spacing: 0.05em;
		background: #0F1117;
		color: #E8E8ED;
		border: 1px solid #2E3240;
		padding: 5px 14px;
		cursor: pointer;
		transition: border-color 0.2s;
	}
	.ctm__btn:hover {
		border-color: #E24B4A;
	}
	.ctm__scrub {
		flex: 1;
		height: 4px;
		accent-color: #E24B4A;
		cursor: pointer;
	}
	.ctm__speed {
		font-family: 'JetBrains Mono', monospace;
		font-size: 11px;
		background: #0F1117;
		color: #E8E8ED;
		border: 1px solid #2E3240;
		padding: 4px 8px;
		cursor: pointer;
	}
	.ctm__legend {
		display: flex;
		align-items: center;
		gap: 1.5rem;
		margin-top: 0.75rem;
		font-family: 'JetBrains Mono', monospace;
		font-size: 10px;
		color: #9CA3AF;
	}
	.ctm__legend-item {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.ctm__legend-dot {
		display: inline-block;
		width: 8px;
		height: 8px;
	}
</style>
