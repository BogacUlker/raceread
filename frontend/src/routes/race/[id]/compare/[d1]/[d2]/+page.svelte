<!--
	Pilot Comparison Page - side-by-side analysis of two drivers.
	Deep-linkable URL: /race/{id}/compare/{d1}/{d2}
-->
<script>
	import { goto } from '$app/navigation';
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
	const chartW = 600;
	const chartH = 150;
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
</script>

<svelte:head>
	<title>{d1} vs {d2} - {raceInfo.name} - RaceRead</title>
</svelte:head>

<section class="compare">
	<!-- Header -->
	<div class="compare__header">
		<a href="/race/{raceId}" class="compare__back">← {raceInfo.name}</a>
		<h1 class="compare__title">
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
		<div class="compare__stat-card">
			<span class="compare__stat-label">{$t('charts.best_lap')}</span>
			<div class="compare__stat-values">
				<span style="color:{teamColor(d1)}">{formatTime(stats.best1)}</span>
				<span style="color:{teamColor(d2)}">{formatTime(stats.best2)}</span>
			</div>
		</div>
		<div class="compare__stat-card">
			<span class="compare__stat-label">{$t('charts.avg_pace')}</span>
			<div class="compare__stat-values">
				<span style="color:{teamColor(d1)}">{formatTime(stats.avg1)}</span>
				<span style="color:{teamColor(d2)}">{formatTime(stats.avg2)}</span>
			</div>
		</div>
		<div class="compare__stat-card">
			<span class="compare__stat-label">{$t('charts.positions')}</span>
			<div class="compare__stat-values">
				<span style="color:{teamColor(d1)}">P{stats.startPos1 ?? '-'} → P{stats.endPos1 ?? '-'}</span>
				<span style="color:{teamColor(d2)}">P{stats.startPos2 ?? '-'} → P{stats.endPos2 ?? '-'}</span>
			</div>
		</div>
		<div class="compare__stat-card">
			<span class="compare__stat-label">{$t('charts.dc_ratio')}</span>
			<div class="compare__stat-values">
				<span style="color:{teamColor(d1)}">{stats.dcRatio1?.toFixed(2) ?? '-'}</span>
				<span style="color:{teamColor(d2)}">{stats.dcRatio2?.toFixed(2) ?? '-'}</span>
			</div>
		</div>
	</div>

	<!-- Speed Trace -->
	<SpeedTrace {raceId} drivers={driverList} {circuit} totalLaps={raceInfo?.total_laps || 58} />

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
	<div class="chart-card">
		<div class="chart-card__header">
			<h3 class="chart-card__title">{$t('charts.sector_comparison')}</h3>
		</div>
		<div class="compare__sectors">
			{#each [['S1', sectorStats.s1_1, sectorStats.s1_2], ['S2', sectorStats.s2_1, sectorStats.s2_2], ['S3', sectorStats.s3_1, sectorStats.s3_2]] as [label, v1, v2]}
				<div class="compare__sector-group">
					<span class="compare__sector-label">{label}</span>
					<div class="compare__sector-bars">
						<div class="compare__sector-bar" style="color:{teamColor(d1)}">
							<span>{d1}</span>
							<span>{v1 != null ? v1.toFixed(3) : '-'}s</span>
						</div>
						<div class="compare__sector-bar" style="color:{teamColor(d2)}">
							<span>{d2}</span>
							<span>{v2 != null ? v2.toFixed(3) : '-'}s</span>
						</div>
						{#if v1 != null && v2 != null}
							<span class="compare__sector-delta">{(v1 - v2) > 0 ? '+' : ''}{(v1 - v2).toFixed(3)}s</span>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	</div>

	<!-- Energy Timeline side by side -->
	<div class="compare__energy-timelines">
		<EnergyTimeline {raceId} drivers={driverList.filter(d => d.driver === d1)} defaultDriver={d1} />
		<EnergyTimeline {raceId} drivers={driverList.filter(d => d.driver === d2)} defaultDriver={d2} />
	</div>

	<!-- Track Maps side by side -->
	<div class="compare__track-maps">
		<TrackMap {raceId} drivers={driverList.filter(d => d.driver === d1)} {circuit} totalLaps={raceInfo?.total_laps || 58} />
		<TrackMap {raceId} drivers={driverList.filter(d => d.driver === d2)} {circuit} totalLaps={raceInfo?.total_laps || 58} />
	</div>
</section>

<style>
	.compare {
		padding-top: var(--space-md);
		display: flex;
		flex-direction: column;
		gap: var(--space-lg);
	}
	.compare__back {
		font-family: var(--font-mono);
		font-size: var(--font-size-small);
		color: var(--text-muted);
	}
	.compare__header {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}
	.compare__title {
		font-family: var(--font-mono);
		font-size: 24px;
		font-weight: 700;
	}
	.compare__vs {
		color: var(--text-muted);
		font-weight: 400;
		font-size: 16px;
		margin: 0 var(--space-sm);
	}
	.compare__selectors {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
	}
	.compare__select {
		font-family: var(--font-mono);
		font-size: var(--font-size-small);
		background: var(--bg-secondary);
		color: var(--text-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 4px 8px;
		cursor: pointer;
	}
	.compare__swap {
		font-size: 16px;
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		color: var(--text-secondary);
		cursor: pointer;
		padding: 2px 8px;
	}
	.compare__swap:hover { color: var(--text-primary); }
	.compare__stats {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: var(--space-md);
	}
	.compare__stat-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: var(--space-md);
	}
	.compare__stat-label {
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.compare__stat-values {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin-top: var(--space-xs);
		font-family: var(--font-mono);
		font-size: 14px;
		font-weight: 600;
	}
	.compare__delta-svg {
		width: 100%;
		max-height: 150px;
	}
	.compare__sectors {
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
	}
	.compare__sector-group {
		display: flex;
		align-items: center;
		gap: var(--space-md);
	}
	.compare__sector-label {
		font-family: var(--font-mono);
		font-size: 14px;
		font-weight: 600;
		color: var(--text-secondary);
		width: 30px;
	}
	.compare__sector-bars {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		flex: 1;
	}
	.compare__sector-bar {
		font-family: var(--font-mono);
		font-size: 13px;
		display: flex;
		gap: var(--space-sm);
	}
	.compare__sector-delta {
		font-family: var(--font-mono);
		font-size: 12px;
		color: var(--text-muted);
	}
	.compare__energy-timelines {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-lg);
	}
	.compare__track-maps {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-lg);
	}
	@media (max-width: 900px) {
		.compare__energy-timelines {
			grid-template-columns: 1fr;
		}
		.compare__track-maps {
			grid-template-columns: 1fr;
		}
		.compare__stats {
			grid-template-columns: repeat(2, 1fr);
		}
	}
</style>
