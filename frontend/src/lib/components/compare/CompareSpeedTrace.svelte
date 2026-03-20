<!--
	CompareSpeedTrace - simplified two-driver speed overlay for compare page.
	Props-only, no store deps, no URL manipulation.
	SVG speed vs distance + throttle strips below.
-->
<script>
	import { onMount } from 'svelte';
	import { scaleLinear } from 'd3-scale';

	let { raceId, driver1, driver2, color1, color2, selectedLap, circuit, totalLaps } = $props();

	let containerEl = $state(null);
	let width = $state(0);
	const margin = { top: 20, right: 20, bottom: 50, left: 50 };
	const mainHeight = 200;
	const throttleHeight = 14;
	const gap = 4;
	const totalHeight = margin.top + mainHeight + gap + throttleHeight + gap + throttleHeight + margin.bottom;

	let telemetryData = $state({});
	let loading = $state(false);
	let hoverX = $state(null);

	function getApiBase() {
		return import.meta.env.VITE_API_URL || 'http://localhost:8000';
	}

	// Fetch telemetry when drivers/lap change
	$effect(() => {
		if (driver1 && driver2 && selectedLap && raceId) {
			fetchComparison();
		}
	});

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

	let d1Data = $derived(telemetryData[driver1]?.samples || []);
	let d2Data = $derived(telemetryData[driver2]?.samples || []);
	let trackLength = $derived(
		circuit?.track_length ||
		(d1Data.length > 0 ? d1Data[d1Data.length - 1]?.dist || 5000 : 5000)
	);

	let innerWidth = $derived(width - margin.left - margin.right);
	let xScale = $derived(scaleLinear().domain([0, trackLength]).range([0, innerWidth]));
	let yScale = $derived(scaleLinear().domain([0, 350]).range([mainHeight, 0]));

	function buildPath(samples) {
		if (!samples.length) return '';
		return samples.map((s, i) => {
			const x = xScale(s.dist || 0);
			const y = yScale(s.speed || 0);
			return `${i === 0 ? 'M' : 'L'}${x},${y}`;
		}).join('');
	}

	function buildThrottleBlocks(samples, stripY) {
		if (samples.length < 2) return [];
		const blocks = [];
		for (let i = 0; i < samples.length - 1; i++) {
			const x1 = xScale(samples[i].dist || 0);
			const x2 = xScale(samples[i + 1].dist || 0);
			let fill = '#1A1D27';
			if (samples[i].brake) fill = '#EF4444';
			else if ((samples[i].throttle || 0) > 50) fill = '#22C55E';
			blocks.push({ x: x1, w: Math.max(1, x2 - x1), y: stripY, fill });
		}
		return blocks;
	}

	let cornerMarkers = $derived.by(() => {
		if (!circuit?.corners) return [];
		return circuit.corners.map(c => ({
			x: xScale(c.distance || 0),
			label: `${c.number}${c.letter || ''}`,
		}));
	});

	function handleMouseMove(e) {
		if (!containerEl) return;
		const svg = containerEl.querySelector('svg');
		if (!svg) return;
		const rect = svg.getBoundingClientRect();
		hoverX = e.clientX - rect.left - margin.left;
	}

	function handleMouseLeave() {
		hoverX = null;
	}

	let hoverInfo = $derived.by(() => {
		if (hoverX === null || !d1Data.length) return null;
		const dist = xScale.invert(hoverX);
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
</script>

<div class="cst" bind:this={containerEl}>
	<div class="cst__header">
		<h3 class="cst__title">SPEED TRACE</h3>
		<span class="cst__lap">LAP {selectedLap}</span>
	</div>

	{#if loading}
		<div class="cst__empty">Loading...</div>
	{:else if d1Data.length === 0 && d2Data.length === 0}
		<div class="cst__empty">No telemetry data</div>
	{:else}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<svg
			{width}
			height={totalHeight}
			class="cst__svg"
			onmousemove={handleMouseMove}
			onmouseleave={handleMouseLeave}
		>
			<g transform="translate({margin.left},{margin.top})">
				<!-- Y axis grid + labels -->
				{#each [0, 50, 100, 150, 200, 250, 300, 350] as tick}
					<line x1={0} y1={yScale(tick)} x2={innerWidth} y2={yScale(tick)} stroke="#2E3240" stroke-opacity="0.4" />
					<text x={-8} y={yScale(tick)} fill="#6B7280" font-size="10" text-anchor="end" dominant-baseline="middle" font-family="'JetBrains Mono', monospace">{tick}</text>
				{/each}

				<!-- Corner markers -->
				{#each cornerMarkers as marker}
					{#if marker.x >= 0 && marker.x <= innerWidth}
						<line x1={marker.x} y1={mainHeight} x2={marker.x} y2={mainHeight + gap + throttleHeight + gap + throttleHeight} stroke="#6B7280" stroke-opacity="0.3" stroke-dasharray="2,2" />
						<text x={marker.x} y={mainHeight + gap + throttleHeight + gap + throttleHeight + 12} fill="#6B7280" font-size="9" text-anchor="middle" font-family="'JetBrains Mono', monospace">
							{marker.label}
						</text>
					{/if}
				{/each}

				<!-- Speed paths -->
				<path d={buildPath(d1Data)} fill="none" stroke={color1} stroke-width="2" />
				<path d={buildPath(d2Data)} fill="none" stroke={color2} stroke-width="2" stroke-opacity="0.85" stroke-dasharray="4,2" />

				<!-- Throttle strip driver 1 -->
				{#each buildThrottleBlocks(d1Data, mainHeight + gap) as block}
					<rect x={block.x} y={block.y} width={block.w} height={throttleHeight / 2} fill={block.fill} />
				{/each}
				<!-- Throttle strip driver 2 -->
				{#each buildThrottleBlocks(d2Data, mainHeight + gap + throttleHeight / 2) as block}
					<rect x={block.x} y={block.y} width={block.w} height={throttleHeight / 2} fill={block.fill} opacity="0.7" />
				{/each}

				<!-- Label between strips -->
				<text x={-8} y={mainHeight + gap + throttleHeight / 2} fill="#6B7280" font-size="8" text-anchor="end" dominant-baseline="middle" font-family="'JetBrains Mono', monospace">THR</text>

				<!-- Second throttle strip (driver 2 dedicated row for clarity) -->
				{#each buildThrottleBlocks(d1Data, mainHeight + gap + throttleHeight + gap) as block}
					<rect x={block.x} y={block.y} width={block.w} height={throttleHeight / 2} fill={block.fill} opacity="0.5" />
				{/each}
				{#each buildThrottleBlocks(d2Data, mainHeight + gap + throttleHeight + gap + throttleHeight / 2) as block}
					<rect x={block.x} y={block.y} width={block.w} height={throttleHeight / 2} fill={block.fill} opacity="0.7" />
				{/each}

				<!-- Hover crosshair -->
				{#if hoverInfo}
					{@const info = hoverInfo}
					<line x1={info.screenX} y1={0} x2={info.screenX} y2={mainHeight + gap + throttleHeight + gap + throttleHeight} stroke="#E8E8ED" stroke-width="1" stroke-dasharray="3,3" stroke-opacity="0.5" />

					<foreignObject
						x={info.screenX > innerWidth / 2 ? info.screenX - 155 : info.screenX + 10}
						y={10}
						width="145"
						height="110"
					>
						<div class="cst__tooltip">
							<div class="cst__tooltip-dist">{info.dist}m</div>
							{#if info.s1}
								<div class="cst__tooltip-row" style="color:{color1}">
									{driver1}: {info.s1.speed?.toFixed(0)} km/h
								</div>
							{/if}
							{#if info.s2}
								<div class="cst__tooltip-row" style="color:{color2}">
									{driver2}: {info.s2.speed?.toFixed(0)} km/h
								</div>
							{/if}
							{#if info.s1 && info.s2}
								{@const delta = (info.s1.speed || 0) - (info.s2.speed || 0)}
								<div class="cst__tooltip-delta" style="color:{delta >= 0 ? color1 : color2}">
									{delta >= 0 ? '+' : ''}{delta.toFixed(0)} km/h
								</div>
							{/if}
						</div>
					</foreignObject>
				{/if}

				<!-- X axis label -->
				<text x={innerWidth / 2} y={mainHeight + gap + throttleHeight + gap + throttleHeight + 28} fill="#6B7280" font-size="11" text-anchor="middle" font-family="'JetBrains Mono', monospace">
					DISTANCE (m)
				</text>
			</g>

			<!-- Legend -->
			<g transform="translate({margin.left},{totalHeight - 10})">
				<rect x={0} y={-4} width={10} height={3} fill={color1} />
				<text x={14} y={0} fill="#9CA3AF" font-size="10" font-family="'JetBrains Mono', monospace">{driver1}</text>
				<rect x={65} y={-4} width={10} height={3} fill={color2} />
				<text x={79} y={0} fill="#9CA3AF" font-size="10" font-family="'JetBrains Mono', monospace">{driver2}</text>
			</g>
		</svg>
	{/if}
</div>

<style>
	.cst {
		background: #1A1D27;
		padding: 1.25rem;
		border-left: 2px solid transparent;
		font-family: 'DM Sans', sans-serif;
		transition: border-color 0.25s, box-shadow 0.25s;
	}
	.cst:hover {
		border-left-color: #E24B4A;
		box-shadow: -4px 0 20px -4px rgba(226, 75, 74, 0.12);
	}
	.cst__header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0.75rem;
	}
	.cst__title {
		font-family: 'Space Grotesk', sans-serif;
		text-transform: uppercase;
		font-size: 15px;
		font-weight: 700;
		color: #E8E8ED;
		margin: 0;
	}
	.cst__lap {
		font-family: 'JetBrains Mono', monospace;
		font-size: 11px;
		color: #6B7280;
		letter-spacing: 0.05em;
	}
	.cst__svg {
		display: block;
		cursor: crosshair;
	}
	.cst__empty {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 200px;
		font-family: 'JetBrains Mono', monospace;
		font-size: 13px;
		color: #6B7280;
	}
	.cst__tooltip {
		background: #22252F;
		border: 1px solid #2E3240;
		padding: 6px 8px;
		font-family: 'JetBrains Mono', monospace;
		font-size: 10px;
		color: #E8E8ED;
	}
	.cst__tooltip-dist {
		color: #6B7280;
		margin-bottom: 4px;
	}
	.cst__tooltip-row {
		line-height: 1.6;
	}
	.cst__tooltip-delta {
		margin-top: 4px;
		font-weight: 600;
	}
</style>
