<!--
	Pilot Comparison Page - side-by-side analysis of two drivers.
	Deep-linkable URL: /race/{id}/compare/{d1}/{d2}
-->
<script>
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS } from '$lib/constants.js';
	import { api } from '$lib/api.js';
	import SpeedTrace from '$lib/components/charts/SpeedTrace.svelte';
	import TrackMap from '$lib/components/charts/TrackMap.svelte';
	import EnergyTimeline from '$lib/components/charts/EnergyTimeline.svelte';

	let { data } = $props();

	let raceId = $derived(data.raceId);
	let raceInfo = $derived(data.raceInfo);
	let d1 = $derived(data.d1);
	let d2 = $derived(data.d2);
	let laps = $derived(data.laps);
	let circuit = $derived(data.circuit);
	let energyComparison = $derived(data.energyComparison);

	// Build driver list
	let driverList = $derived(laps.map(d => ({ driver: d.driver, team: d.team })));
	let allDriverCodes = $derived(driverList.map(d => d.driver));

	// Driver selectors
	let sel1 = $state('');

	// Auto-select compare mode on track map after render
	onMount(() => {
		setTimeout(() => {
			const btns = document.querySelectorAll('.track-map__mode-btn');
			btns.forEach(btn => {
				if (btn.textContent.trim().toLowerCase().includes('kar') || btn.textContent.trim().toLowerCase().includes('compare')) {
					btn.click();
				}
			});
		}, 500);
	});
	let sel2 = $state('');

	$effect(() => {
		sel1 = d1;
		sel2 = d2;
	});

	function swapDrivers() {
		goto(`/race/${raceId}/compare/${sel2}/${sel1}`);
	}

	function navigateCompare() {
		if (sel1 && sel2 && sel1 !== sel2) {
			goto(`/race/${raceId}/compare/${sel1}/${sel2}`);
		}
	}

	// Driver data helpers
	function getDriverLaps(code) {
		const entry = laps.find(d => d.driver === code);
		return entry?.laps || [];
	}

	function getTeam(code) {
		const entry = laps.find(d => d.driver === code);
		return entry?.team || 'Unknown';
	}

	function teamColor(code) {
		return TEAM_COLORS[getTeam(code)] || '#888';
	}

	// Stats
	let stats = $derived.by(() => {
		const l1 = getDriverLaps(d1).filter(l => l.time_s != null && l.is_accurate !== false);
		const l2 = getDriverLaps(d2).filter(l => l.time_s != null && l.is_accurate !== false);

		const best1 = l1.length ? Math.min(...l1.map(l => l.time_s)) : null;
		const best2 = l2.length ? Math.min(...l2.map(l => l.time_s)) : null;
		const avg1 = l1.length ? l1.reduce((s, l) => s + l.time_s, 0) / l1.length : null;
		const avg2 = l2.length ? l2.reduce((s, l) => s + l.time_s, 0) / l2.length : null;

		const lastLap1 = getDriverLaps(d1).filter(l => l.position != null).at(-1);
		const lastLap2 = getDriverLaps(d2).filter(l => l.position != null).at(-1);
		const firstLap1 = getDriverLaps(d1).find(l => l.position != null);
		const firstLap2 = getDriverLaps(d2).find(l => l.position != null);

		const e1 = (energyComparison.entries || []).find(e => e.driver === d1);
		const e2 = (energyComparison.entries || []).find(e => e.driver === d2);

		return {
			best1, best2, avg1, avg2,
			startPos1: firstLap1?.position, startPos2: firstLap2?.position,
			endPos1: lastLap1?.position, endPos2: lastLap2?.position,
			dcRatio1: e1?.dc_ratio, dcRatio2: e2?.dc_ratio,
		};
	});

	function formatTime(s) {
		if (s == null) return '-';
		const mins = Math.floor(s / 60);
		const secs = s % 60;
		return mins > 0 ? `${mins}:${secs.toFixed(3).padStart(6, '0')}` : secs.toFixed(3);
	}

	// Lap delta (d1 - d2 per lap)
	let lapDeltas = $derived.by(() => {
		const l1 = getDriverLaps(d1);
		const l2 = getDriverLaps(d2);
		const map2 = Object.fromEntries(l2.map(l => [l.lap, l.time_s]));

		return l1
			.filter(l => l.time_s != null && l.is_accurate !== false && map2[l.lap] != null)
			.map(l => ({
				lap: l.lap,
				delta: +(l.time_s - map2[l.lap]).toFixed(3),
			}));
	});

	// Sector comparison
	let sectorStats = $derived.by(() => {
		const l1 = getDriverLaps(d1).filter(l => l.s1 != null && l.s2 != null && l.s3 != null && l.is_accurate !== false);
		const l2 = getDriverLaps(d2).filter(l => l.s1 != null && l.s2 != null && l.s3 != null && l.is_accurate !== false);

		const median = (arr) => {
			if (!arr.length) return null;
			const s = [...arr].sort((a, b) => a - b);
			return s[Math.floor(s.length / 2)];
		};

		return {
			s1_1: median(l1.map(l => l.s1)), s1_2: median(l2.map(l => l.s1)),
			s2_1: median(l1.map(l => l.s2)), s2_2: median(l2.map(l => l.s2)),
			s3_1: median(l1.map(l => l.s3)), s3_2: median(l2.map(l => l.s3)),
		};
	});

	// Simple SVG chart dimensions
	const chartW = 1200;
	const chartH = 200;
	const chartM = { top: 10, right: 10, bottom: 30, left: 40 };

	// Delta chart scales
	let deltaMaxD = $derived(Math.max(0.5, ...lapDeltas.map(d => Math.abs(d.delta))));
	function deltaXScale(lap) {
		if (lapDeltas.length < 2) return chartM.left;
		return chartM.left + ((lap - lapDeltas[0].lap) / (lapDeltas[lapDeltas.length - 1].lap - lapDeltas[0].lap)) * (chartW - chartM.left - chartM.right);
	}
	function deltaYScale(val) {
		return chartM.top + ((deltaMaxD - val) / (2 * deltaMaxD)) * (chartH - chartM.top - chartM.bottom);
	}

	// Uppercase race name with proper GRAND PRIX (not PRİX)
	function gpName(name) {
		if (!name) return '';
		const parts = name.split('Grand Prix');
		if (parts.length === 2) return parts[0].toUpperCase() + 'GRAND PRIX';
		return name.toUpperCase();
	}

	</script>

<svelte:head>
	<title>{d1} vs {d2} - {raceInfo.name} - RaceRead</title>
	<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" />
</svelte:head>

<section class="compare">
	<!-- Header -->
	<div class="compare__header">
		<a href="/race/{raceId}" class="compare__back">← {raceInfo.name}</a>
		<h1 class="compare__title" style="text-transform:none">
			<span style="color:{teamColor(d1)}">{d1}</span>
			<span class="compare__vs">{$t('charts.vs')}</span>
			<span style="color:{teamColor(d2)}">{d2}</span>
		</h1>
		<!-- Driver selector -->
		<div class="compare__selectors">
			<select bind:value={sel1} class="compare__select" onchange={navigateCompare}>
				{#each allDriverCodes as code}
					<option value={code}>{code}</option>
				{/each}
			</select>
			<button class="compare__swap" onclick={swapDrivers}>⇄</button>
			<select bind:value={sel2} class="compare__select" onchange={navigateCompare}>
				{#each allDriverCodes as code}
					<option value={code}>{code}</option>
				{/each}
			</select>
		</div>
	</div>

	<!-- Stats Cards -->
	<div class="compare__stats">
		<div class="compare__stat-card compare__stat-card--accent">
			<span class="compare__stat-label">{$t('charts.best_lap')}</span>
			<div class="compare__stat-row">
				<div class="compare__stat-driver">
					<span class="compare__stat-code" style="color:{teamColor(d1)}">{d1}</span>
					<span class="compare__stat-big" style="color:{teamColor(d1)}">{formatTime(stats.best1)}</span>
				</div>
				<div class="compare__stat-driver">
					<span class="compare__stat-code" style="color:{teamColor(d2)}">{d2}</span>
					<span class="compare__stat-big" style="color:{teamColor(d2)}">{formatTime(stats.best2)}</span>
				</div>
			</div>
		</div>
		<div class="compare__stat-card">
			<span class="compare__stat-label">{$t('charts.avg_pace')}</span>
			<div class="compare__stat-row">
				<div class="compare__stat-driver">
					<span class="compare__stat-code" style="color:{teamColor(d1)}">{d1}</span>
					<span class="compare__stat-big" style="color:{teamColor(d1)}">{formatTime(stats.avg1)}</span>
				</div>
				<div class="compare__stat-driver">
					<span class="compare__stat-code" style="color:{teamColor(d2)}">{d2}</span>
					<span class="compare__stat-big" style="color:{teamColor(d2)}">{formatTime(stats.avg2)}</span>
				</div>
			</div>
		</div>
		<div class="compare__stat-card">
			<span class="compare__stat-label">{$t('charts.positions')}</span>
			<div class="compare__stat-row">
				<div class="compare__stat-driver">
					<span class="compare__stat-code" style="color:{teamColor(d1)}">{d1}</span>
					<span class="compare__stat-big" style="color:{teamColor(d1)}">P{stats.startPos1 ?? '-'} → P{stats.endPos1 ?? '-'}</span>
				</div>
				<div class="compare__stat-driver">
					<span class="compare__stat-code" style="color:{teamColor(d2)}">{d2}</span>
					<span class="compare__stat-big" style="color:{teamColor(d2)}">P{stats.startPos2 ?? '-'} → P{stats.endPos2 ?? '-'}</span>
				</div>
			</div>
		</div>
		<div class="compare__stat-card">
			<span class="compare__stat-label">{$t('charts.dc_ratio')}</span>
			<div class="compare__stat-row">
				<div class="compare__stat-driver">
					<span class="compare__stat-code" style="color:{teamColor(d1)}">{d1}</span>
					<span class="compare__stat-big" style="color:{teamColor(d1)}">{stats.dcRatio1?.toFixed(2) ?? '-'}</span>
				</div>
				<div class="compare__stat-driver">
					<span class="compare__stat-code" style="color:{teamColor(d2)}">{d2}</span>
					<span class="compare__stat-big" style="color:{teamColor(d2)}">{stats.dcRatio2?.toFixed(2) ?? '-'}</span>
				</div>
			</div>
		</div>
	</div>

	<!-- Speed Trace -->
	<SpeedTrace {raceId} drivers={[
		...driverList.filter(d => d.driver === d1),
		...driverList.filter(d => d.driver === d2),
		...driverList.filter(d => d.driver !== d1 && d.driver !== d2)
	]} {circuit} totalLaps={raceInfo?.total_laps || 58} compareDriver1={d1} compareDriver2={d2} />

	<!-- Lap Delta Chart -->
	{#if lapDeltas.length > 0}
		<div class="chart-card">
			<div class="chart-card__header">
				<h3 class="chart-card__title">{$t('charts.lap_delta')}</h3>
			</div>
			<svg viewBox="0 0 {chartW} {chartH}" class="compare__delta-svg">
				<!-- Zero line -->
				<line x1={chartM.left} y1={deltaYScale(0)} x2={chartW - chartM.right} y2={deltaYScale(0)} stroke="var(--text-muted)" stroke-opacity="0.5" />
				<!-- Lines -->
				{#each lapDeltas as d, i}
					{#if i > 0}
						{@const prevD = lapDeltas[i - 1]}
						<line
							x1={deltaXScale(prevD.lap)} y1={deltaYScale(prevD.delta)}
							x2={deltaXScale(d.lap)} y2={deltaYScale(d.delta)}
							stroke={d.delta > 0 ? teamColor(d2) : teamColor(d1)}
							stroke-width="2"
						/>
					{/if}
				{/each}
				<!-- Labels -->
				<text x={chartM.left - 4} y={deltaYScale(deltaMaxD)} fill="var(--text-muted)" font-size="9" text-anchor="end" font-family="var(--font-mono)">{d2} {$t('charts.faster')}</text>
				<text x={chartM.left - 4} y={deltaYScale(-deltaMaxD)} fill="var(--text-muted)" font-size="9" text-anchor="end" font-family="var(--font-mono)">{d1} {$t('charts.faster')}</text>
				<text x={chartW / 2} y={chartH - 4} fill="var(--text-muted)" font-size="9" text-anchor="middle" font-family="var(--font-mono)">{$t('common.lap')}</text>
			</svg>
		</div>
	{/if}

	<!-- Sector Comparison -->
	<!-- Sector Comparison Cards -->
	<div class="compare__sector-cards">
		{#each [['S1', sectorStats.s1_1, sectorStats.s1_2], ['S2', sectorStats.s2_1, sectorStats.s2_2], ['S3', sectorStats.s3_1, sectorStats.s3_2]] as [label, v1, v2]}
			{@const delta = (v1 != null && v2 != null) ? v1 - v2 : null}
			{@const winner = delta != null ? (delta < 0 ? d1 : d2) : null}
			<div class="compare__sec-card" style="border-left-color:{winner ? teamColor(winner) : 'var(--brd)'}">
				<span class="compare__sec-label">{label}</span>
				<div class="compare__sec-times">
					<div class="compare__sec-row">
						<span class="compare__sec-code" style="color:{teamColor(d1)}">{d1}</span>
						<span class="compare__sec-val" class:compare__sec-val--best={delta != null && delta < 0}>{v1 != null ? v1.toFixed(3) + 's' : '-'}</span>
					</div>
					<div class="compare__sec-row">
						<span class="compare__sec-code" style="color:{teamColor(d2)}">{d2}</span>
						<span class="compare__sec-val" class:compare__sec-val--best={delta != null && delta > 0}>{v2 != null ? v2.toFixed(3) + 's' : '-'}</span>
					</div>
				</div>
				{#if delta != null}
					<span class="compare__sec-delta" style="color:{teamColor(winner)}">{delta > 0 ? '+' : ''}{delta.toFixed(3)}s</span>
				{/if}
			</div>
		{/each}
	</div>

	<!-- Energy Timeline side by side -->
	<div class="compare__energy-timelines">
		<EnergyTimeline {raceId} drivers={driverList.filter(d => d.driver === d1)} defaultDriver={d1} compareDriver={d1} />
		<EnergyTimeline {raceId} drivers={driverList.filter(d => d.driver === d2)} defaultDriver={d2} compareDriver={d2} />
	</div>

	<!-- Track Map - compare mode -->
	<TrackMap {raceId} drivers={[
		...driverList.filter(d => d.driver === d1),
		...driverList.filter(d => d.driver === d2),
		...driverList.filter(d => d.driver !== d1 && d.driver !== d2)
	]} {circuit} totalLaps={raceInfo?.total_laps || 58} compareDriver1={d1} compareDriver2={d2} />
</section>

<style>
	/* ═══ PREVIEW COMPARE PAGE ═══ */
	.compare {
		position: fixed; inset: 0; z-index: 200;
		overflow-y: auto; overflow-x: hidden;
		background: #0F1117; color: #E8E8ED;
		font-family: 'DM Sans', sans-serif;
		-webkit-font-smoothing: antialiased;
		padding: 1.5rem 2rem 3rem;
		display: flex; flex-direction: column; gap: 1.5rem;
		--fm: 'JetBrains Mono', monospace;
		--fh: 'Space Grotesk', sans-serif;
		--ac: #E24B4A; --bg2: #1A1D27; --bgc: #22252F; --brd: #2E3240; --tm: #6B7280;
	}
	.compare :global(*) { border-radius: 0 !important; }
	.compare :global(.chart-card) { border-radius: 0 !important; border: none !important; background: var(--bg2) !important; border-left: 2px solid transparent !important; transition: border-color .25s, box-shadow .25s !important; }
	.compare :global(.chart-card:hover) { border-left-color: var(--ac) !important; box-shadow: -4px 0 20px -4px rgba(226,75,74,.12) !important; }
	.compare :global(.chart-card__title) { font-family: var(--fh) !important; text-transform: uppercase; letter-spacing: .03em; }

	.compare__back { font-family: var(--fm); font-size: 11px; color: var(--ac); text-decoration: none; letter-spacing: .08em; }
	.compare__back:hover { text-decoration: none; opacity: .8; }
	.compare__header { display: flex; flex-direction: column; gap: .5rem; }
	.compare__title { font-family: var(--fh); font-size: 28px; font-weight: 700; text-transform: uppercase; letter-spacing: -.02em; }
	.compare__vs { color: var(--tm); font-weight: 400; font-size: 18px; margin: 0 .5rem; }
	.compare__selectors { display: flex; align-items: center; gap: .5rem; }
	.compare__select { font-family: var(--fm); font-size: 12px; background: #0F1117; color: #E8E8ED; border: 1px solid var(--brd); padding: 5px 8px; cursor: pointer; }
	.compare__swap { font-size: 16px; background: none; border: 1px solid var(--brd); color: #9CA3AF; cursor: pointer; padding: 3px 10px; transition: all .15s; }
	.compare__swap:hover { color: var(--ac); border-color: var(--ac); }

	/* Stats cards - overview style */
	.compare__stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 2px; }
	.compare__stat-card { background: var(--bg2); padding: 1.3rem 1.5rem; border-left: 3px solid var(--brd); transition: border-color .2s; }
	.compare__stat-card:hover { border-left-color: var(--ac); }
	.compare__stat-card--accent { border-left-color: var(--ac); background: linear-gradient(135deg, var(--bg2) 0%, rgba(226,75,74,.06) 100%); }
	.compare__stat-label { font-family: var(--fm); font-size: 9px; color: var(--tm); text-transform: uppercase; letter-spacing: .12em; margin-bottom: .75rem; display: block; }
	.compare__stat-row { display: flex; justify-content: space-between; gap: .75rem; }
	.compare__stat-driver { display: flex; flex-direction: column; gap: 2px; }
	.compare__stat-code { font-family: var(--fm); font-size: 10px; font-weight: 700; }
	.compare__stat-big { font-family: var(--fh); font-size: 22px; font-weight: 700; line-height: 1; }

	/* Lap delta chart */
	.compare__delta-svg { width: 100%; max-height: 180px; }

	/* Sectors */
	.compare__sector-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px; }
	.compare__sec-card { background: var(--bg2); padding: 1.3rem 1.5rem; border-left: 3px solid var(--brd); transition: border-color .2s; }
	.compare__sec-card:hover { border-left-color: var(--ac); }
	.compare__sec-label { font-family: var(--fh); font-size: 20px; font-weight: 700; color: #E8E8ED; display: block; margin-bottom: .75rem; }
	.compare__sec-times { display: flex; flex-direction: column; gap: .4rem; }
	.compare__sec-row { display: flex; justify-content: space-between; align-items: center; }
	.compare__sec-code { font-family: var(--fm); font-size: 11px; font-weight: 700; }
	.compare__sec-val { font-family: var(--fm); font-size: 15px; font-weight: 600; color: #9CA3AF; }
	.compare__sec-val--best { color: #22C55E; }
	.compare__sec-delta { display: block; margin-top: .5rem; font-family: var(--fm); font-size: 12px; font-weight: 700; }

	/* Energy timelines + track maps side by side */
	.compare__energy-timelines { display: grid; grid-template-columns: 1fr 1fr; gap: 3px; }
	

	@media (max-width: 1100px) {
		.compare__stats { grid-template-columns: repeat(2, 1fr); }
		.compare__sector-cards { grid-template-columns: 1fr; }
	}
	@media (max-width: 900px) {
		.compare__energy-timelines { grid-template-columns: 1fr; }
		.compare { padding: 1rem; }
	}
	@media (max-width: 480px) {
		.compare__stats { grid-template-columns: 1fr; }
		.compare__title { font-size: 20px; }
	}
</style>