<!--
	CompareEnergyTimeline - side-by-side energy timelines for compare page.
	Props-only, no store deps. Two stacked bar charts (deploy/harvest/clip).
	Shows "inferred" badge on each panel.
-->
<script>
	import { onMount } from 'svelte';
	import { scaleLinear, scaleBand } from 'd3-scale';

	let { raceId, driver1, driver2, color1, color2 } = $props();

	let containerEl = $state(null);
	let containerWidth = $state(500);
	let energy1 = $state(null);
	let energy2 = $state(null);
	let loading1 = $state(false);
	let loading2 = $state(false);
	let hoverLap1 = $state(null);
	let hoverLap2 = $state(null);

	const ENERGY = {
		deploy: '#22C55E',
		harvest: '#3B82F6',
		clip: '#F59E0B',
	};

	const margin = { top: 8, right: 12, bottom: 28, left: 32 };
	const chartHeight = 180;

	function getApiBase() {
		return import.meta.env.VITE_API_URL || 'http://localhost:8000';
	}

	$effect(() => {
		if (driver1 && raceId) fetchEnergy(driver1, 1);
	});

	$effect(() => {
		if (driver2 && raceId) fetchEnergy(driver2, 2);
	});

	async function fetchEnergy(driver, slot) {
		if (slot === 1) loading1 = true;
		else loading2 = true;
		try {
			const base = getApiBase();
			const res = await fetch(`${base}/api/races/${raceId}/energy?driver=${driver}`);
			if (res.ok) {
				const data = await res.json();
				if (slot === 1) energy1 = data;
				else energy2 = data;
			}
		} catch { /* ignore */ }
		if (slot === 1) loading1 = false;
		else loading2 = false;
	}

	let laps1 = $derived(energy1?.laps ?? []);
	let laps2 = $derived(energy2?.laps ?? []);

	let panelWidth = $derived(Math.max(200, (containerWidth - 3) / 2));
	let innerWidth = $derived(panelWidth - margin.left - margin.right);

	function buildScales(laps) {
		const lapNums = laps.map(l => l.lap);
		const x = scaleBand().domain(lapNums).range([0, innerWidth]).padding(0.15);
		const y = scaleLinear().domain([0, 100]).range([chartHeight, 0]);
		return { x, y };
	}

	function buildBars(laps, scales) {
		if (!laps.length) return [];
		const { x, y } = scales;
		return laps.map(lap => {
			const bw = x.bandwidth();
			const xPos = x(lap.lap) || 0;
			// Normalized values: deploy + harvest + clip = ~100
			const norm = { deploy: lap.normalized_deploy, harvest: lap.normalized_harvest, clip: lap.normalized_clip };
			const deploy = norm.deploy ?? 0;
			const harvest = norm.harvest ?? 0;
			const clip = norm.clip ?? 0;

			// Stack: harvest at bottom, deploy middle, clip top
			const harvestH = (harvest / 100) * chartHeight;
			const deployH = (deploy / 100) * chartHeight;
			const clipH = (clip / 100) * chartHeight;

			return {
				lap: lap.lap,
				x: xPos,
				w: bw,
				harvest: { y: chartHeight - harvestH, h: harvestH },
				deploy: { y: chartHeight - harvestH - deployH, h: deployH },
				clip: { y: chartHeight - harvestH - deployH - clipH, h: clipH },
				raw: lap,
			};
		});
	}

	let scales1 = $derived(buildScales(laps1));
	let scales2 = $derived(buildScales(laps2));
	let bars1 = $derived(buildBars(laps1, scales1));
	let bars2 = $derived(buildBars(laps2, scales2));

	// X-axis tick labels (show every Nth lap)
	function xTicks(laps) {
		if (laps.length <= 15) return laps.map(l => l.lap);
		const step = Math.ceil(laps.length / 12);
		return laps.filter((_, i) => i % step === 0).map(l => l.lap);
	}

	let ticks1 = $derived(xTicks(laps1));
	let ticks2 = $derived(xTicks(laps2));

	// Hover tooltip data
	function getHoverData(bars, hoverLap) {
		if (hoverLap === null) return null;
		return bars.find(b => b.lap === hoverLap);
	}

	let hover1 = $derived(getHoverData(bars1, hoverLap1));
	let hover2 = $derived(getHoverData(bars2, hoverLap2));

	function handleBarHover(panel, lap) {
		if (panel === 1) hoverLap1 = lap;
		else hoverLap2 = lap;
	}

	function handleBarLeave(panel) {
		if (panel === 1) hoverLap1 = null;
		else hoverLap2 = null;
	}

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

<div class="cet" bind:this={containerEl}>
	<div class="cet__panels">
		<!-- Driver 1 panel -->
		<div class="cet__panel">
			<div class="cet__panel-header">
				<span class="cet__driver" style="color:{color1}">{driver1}</span>
				<span class="cet__title">ENERGY TIMELINE</span>
				<span class="cet__inferred">INFERRED</span>
			</div>

			{#if loading1}
				<div class="cet__empty">Loading...</div>
			{:else if bars1.length === 0}
				<div class="cet__empty">No data</div>
			{:else}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<svg width={panelWidth} height={chartHeight + margin.top + margin.bottom} class="cet__svg">
					<g transform="translate({margin.left},{margin.top})">
						<!-- Y axis -->
						{#each [0, 25, 50, 75, 100] as tick}
							<line x1={0} y1={scales1.y(tick)} x2={innerWidth} y2={scales1.y(tick)} stroke="#2E3240" stroke-opacity="0.4" />
							<text x={-6} y={scales1.y(tick)} fill="#6B7280" font-size="9" text-anchor="end" dominant-baseline="middle" font-family="'JetBrains Mono', monospace">{tick}</text>
						{/each}

						<!-- Bars -->
						{#each bars1 as bar}
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<g
								onmouseenter={() => handleBarHover(1, bar.lap)}
								onmouseleave={() => handleBarLeave(1)}
								style="cursor:crosshair"
							>
								<rect x={bar.x} y={bar.harvest.y} width={bar.w} height={bar.harvest.h} fill={ENERGY.harvest} opacity={hoverLap1 === bar.lap ? 1 : 0.85} />
								<rect x={bar.x} y={bar.deploy.y} width={bar.w} height={bar.deploy.h} fill={ENERGY.deploy} opacity={hoverLap1 === bar.lap ? 1 : 0.85} />
								<rect x={bar.x} y={bar.clip.y} width={bar.w} height={bar.clip.h} fill={ENERGY.clip} opacity={hoverLap1 === bar.lap ? 1 : 0.85} />
								<!-- Invisible hit area -->
								<rect x={bar.x} y={0} width={bar.w} height={chartHeight} fill="transparent" />
							</g>
						{/each}

						<!-- X axis ticks -->
						{#each ticks1 as tick}
							{@const xPos = (scales1.x(tick) || 0) + scales1.x.bandwidth() / 2}
							<text x={xPos} y={chartHeight + 16} fill="#6B7280" font-size="9" text-anchor="middle" font-family="'JetBrains Mono', monospace">{tick}</text>
						{/each}

					</g>
				</svg>
				<!-- Hover tooltip (HTML, outside SVG) -->
				{#if hover1}
					{@const norm = { deploy: hover1.raw.normalized_deploy, harvest: hover1.raw.normalized_harvest, clip: hover1.raw.normalized_clip }}
					<div class="cet__tip" style="left:{hover1.x + hover1.w + 50}px; top:30px;">
						<div class="cet__tip-lap">LAP {hover1.lap}</div>
						<div style="color:{ENERGY.deploy}">Deploy: {(norm.deploy ?? 0).toFixed(1)}%</div>
						<div style="color:{ENERGY.harvest}">Harvest: {(norm.harvest ?? 0).toFixed(1)}%</div>
						<div style="color:{ENERGY.clip}">Clip: {(norm.clip ?? 0).toFixed(1)}%</div>
					</div>
				{/if}
			{/if}
		</div>

		<!-- Driver 2 panel -->
		<div class="cet__panel">
			<div class="cet__panel-header">
				<span class="cet__driver" style="color:{color2}">{driver2}</span>
				<span class="cet__title">ENERGY TIMELINE</span>
				<span class="cet__inferred">INFERRED</span>
			</div>

			{#if loading2}
				<div class="cet__empty">Loading...</div>
			{:else if bars2.length === 0}
				<div class="cet__empty">No data</div>
			{:else}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<svg width={panelWidth} height={chartHeight + margin.top + margin.bottom} class="cet__svg">
					<g transform="translate({margin.left},{margin.top})">
						<!-- Y axis -->
						{#each [0, 25, 50, 75, 100] as tick}
							<line x1={0} y1={scales2.y(tick)} x2={innerWidth} y2={scales2.y(tick)} stroke="#2E3240" stroke-opacity="0.4" />
							<text x={-6} y={scales2.y(tick)} fill="#6B7280" font-size="9" text-anchor="end" dominant-baseline="middle" font-family="'JetBrains Mono', monospace">{tick}</text>
						{/each}

						<!-- Bars -->
						{#each bars2 as bar}
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<g
								onmouseenter={() => handleBarHover(2, bar.lap)}
								onmouseleave={() => handleBarLeave(2)}
								style="cursor:crosshair"
							>
								<rect x={bar.x} y={bar.harvest.y} width={bar.w} height={bar.harvest.h} fill={ENERGY.harvest} opacity={hoverLap2 === bar.lap ? 1 : 0.85} />
								<rect x={bar.x} y={bar.deploy.y} width={bar.w} height={bar.deploy.h} fill={ENERGY.deploy} opacity={hoverLap2 === bar.lap ? 1 : 0.85} />
								<rect x={bar.x} y={bar.clip.y} width={bar.w} height={bar.clip.h} fill={ENERGY.clip} opacity={hoverLap2 === bar.lap ? 1 : 0.85} />
								<rect x={bar.x} y={0} width={bar.w} height={chartHeight} fill="transparent" />
							</g>
						{/each}

						<!-- X axis ticks -->
						{#each ticks2 as tick}
							{@const xPos = (scales2.x(tick) || 0) + scales2.x.bandwidth() / 2}
							<text x={xPos} y={chartHeight + 16} fill="#6B7280" font-size="9" text-anchor="middle" font-family="'JetBrains Mono', monospace">{tick}</text>
						{/each}

					</g>
				</svg>
				{#if hover2}
					{@const norm = { deploy: hover2.raw.normalized_deploy, harvest: hover2.raw.normalized_harvest, clip: hover2.raw.normalized_clip }}
					<div class="cet__tip" style="left:{hover2.x + hover2.w + 50}px; top:30px;">
						<div class="cet__tip-lap">LAP {hover2.lap}</div>
						<div style="color:{ENERGY.deploy}">Deploy: {(norm.deploy ?? 0).toFixed(1)}%</div>
						<div style="color:{ENERGY.harvest}">Harvest: {(norm.harvest ?? 0).toFixed(1)}%</div>
						<div style="color:{ENERGY.clip}">Clip: {(norm.clip ?? 0).toFixed(1)}%</div>
					</div>
				{/if}
			{/if}
		</div>
	</div>

	<!-- Shared legend -->
	<div class="cet__legend">
		<span class="cet__legend-item">
			<span class="cet__legend-dot" style="background:{ENERGY.deploy}"></span>
			DEPLOY
		</span>
		<span class="cet__legend-item">
			<span class="cet__legend-dot" style="background:{ENERGY.harvest}"></span>
			HARVEST
		</span>
		<span class="cet__legend-item">
			<span class="cet__legend-dot" style="background:{ENERGY.clip}"></span>
			CLIP
		</span>
	</div>
</div>

<style>
	.cet {
		background: #1A1D27;
		padding: 1.25rem;
		border-left: 2px solid transparent;
		font-family: 'DM Sans', sans-serif;
		transition: border-color 0.25s, box-shadow 0.25s;
	}
	.cet:hover {
		border-left-color: #E24B4A;
		box-shadow: -4px 0 20px -4px rgba(226, 75, 74, 0.12);
	}
	.cet__panels {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 3px;
	}
	.cet__panel { position: relative;
		background: #0F1117;
		padding: 0.75rem;
	}
	.cet__panel-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 0.5rem;
	}
	.cet__driver {
		font-family: 'JetBrains Mono', monospace;
		font-size: 13px;
		font-weight: 700;
	}
	.cet__title {
		font-family: 'Space Grotesk', sans-serif;
		text-transform: uppercase;
		font-size: 11px;
		font-weight: 600;
		color: #6B7280;
		letter-spacing: 0.05em;
	}
	.cet__inferred {
		display: inline-block;
		font-family: 'JetBrains Mono', monospace;
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		background: #22C55E;
		color: #000;
		padding: 1px 6px;
		line-height: 1.4;
		margin-left: auto;
	}
	.cet__svg {
		display: block;
		width: 100%;
		height: auto;
	}
	.cet__empty {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 180px;
		font-family: 'JetBrains Mono', monospace;
		font-size: 13px;
		color: #6B7280;
	}
	.cet__tip {
		position: absolute;
		background: rgba(15, 17, 23, 0.95);
		border: 1px solid #2E3240;
		padding: 10px 14px;
		font-family: 'JetBrains Mono', monospace;
		font-size: 13px;
		color: #E8E8ED;
		line-height: 1.7;
		white-space: nowrap;
		pointer-events: none;
		z-index: 50;
		box-shadow: 0 4px 20px rgba(0,0,0,.5);
	}
	.cet__tip-lap {
		color: #9CA3AF;
		margin-bottom: 4px;
		font-weight: 700;
		font-size: 12px;
		letter-spacing: .04em;
	}
	.cet__legend {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 1.5rem;
		margin-top: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid #2E3240;
		font-family: 'JetBrains Mono', monospace;
		font-size: 13px;
		color: #9CA3AF;
		letter-spacing: 0.05em;
	}
	.cet__legend-item {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.cet__legend-dot {
		display: inline-block;
		width: 8px;
		height: 8px;
	}

	@media (max-width: 768px) {
		.cet__panels {
			grid-template-columns: 1fr;
		}
	}
</style>
