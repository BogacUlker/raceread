<script>
	import { t, locale } from '$lib/i18n/index.js';
	import { TEAM_COLORS } from '$lib/constants.js';
	import CompareSpeedTrace from '$lib/components/compare/CompareSpeedTrace.svelte';
	import CompareTrackMap from '$lib/components/compare/CompareTrackMap.svelte';
	import CompareEnergyTimeline from '$lib/components/compare/CompareEnergyTimeline.svelte';

	let { data } = $props();
	let raceId = $derived(data.raceId);
	let raceInfo = $derived(data.raceInfo);
	let laps = $derived(data.laps);
	let circuit = $derived(data.circuit);
	let energyComparison = $derived(data.energyComparison);

	let driverList = $derived(laps.map(d => ({ driver: d.driver, team: d.team })));
	let allCodes = $derived(driverList.map(d => d.driver));

	// Local state - no URL, no stores, no goto
	let pick1 = $state('');
	let pick2 = $state('');
	let selectedLap = $state(5);
	let ready = $derived(pick1 !== '' && pick2 !== '' && pick1 !== pick2);

	function teamColor(code) { const d = driverList.find(x => x.driver === code); return TEAM_COLORS[d?.team] || '#888'; }
	function getTeam(code) { const d = driverList.find(x => x.driver === code); return d?.team || ''; }
	function formatTime(s) { if (s == null) return '-'; const m = Math.floor(s / 60); const sec = s % 60; return m > 0 ? m + ':' + sec.toFixed(3).padStart(6, '0') : sec.toFixed(3); }
	function gpName(name) { if (!name) return ''; const p = name.split('Grand Prix'); return p.length === 2 ? p[0].toUpperCase() + 'GRAND PRIX' : name.toUpperCase(); }

	let color1 = $derived(teamColor(pick1));
	let color2 = $derived(teamColor(pick2));

	// Stats
	let stats = $derived.by(() => {
		if (!ready) return null;
		const l1 = (laps.find(d => d.driver === pick1)?.laps || []).filter(l => l.time_s != null && l.is_accurate !== false);
		const l2 = (laps.find(d => d.driver === pick2)?.laps || []).filter(l => l.time_s != null && l.is_accurate !== false);
		const best1 = l1.length ? Math.min(...l1.map(l => l.time_s)) : null;
		const best2 = l2.length ? Math.min(...l2.map(l => l.time_s)) : null;
		const avg1 = l1.length ? l1.reduce((s, l) => s + l.time_s, 0) / l1.length : null;
		const avg2 = l2.length ? l2.reduce((s, l) => s + l.time_s, 0) / l2.length : null;
		const e1 = (energyComparison.entries || []).find(e => e.driver === pick1);
		const e2 = (energyComparison.entries || []).find(e => e.driver === pick2);
		const median = arr => { if (!arr.length) return null; const s = [...arr].sort((a,b)=>a-b); return s[Math.floor(s.length/2)]; };
		const sl1 = l1.filter(l => l.s1 && l.s2 && l.s3);
		const sl2 = l2.filter(l => l.s1 && l.s2 && l.s3);
		return {
			best1, best2, avg1, avg2, dc1: e1?.dc_ratio, dc2: e2?.dc_ratio,
			s1_1: median(sl1.map(l=>l.s1)), s1_2: median(sl2.map(l=>l.s1)),
			s2_1: median(sl1.map(l=>l.s2)), s2_2: median(sl2.map(l=>l.s2)),
			s3_1: median(sl1.map(l=>l.s3)), s3_2: median(sl2.map(l=>l.s3)),
		};
	});

	let lapOptions = $derived(Array.from({length: raceInfo.total_laps || 58}, (_, i) => i + 1));
</script>

<svelte:head>
	<title>{pick1 && pick2 ? pick1 + ' vs ' + pick2 + ' - ' : ''}{raceInfo.name} - RaceRead</title>
	<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" />
</svelte:head>

<div class="cmp">
	<div class="cmp__header">
		<a href="/race/{raceId}" class="cmp__back">&larr; {gpName(raceInfo.name)}</a>
		<h1 class="cmp__title">{$t('charts.compare')}</h1>
	</div>

	<!-- Control bar: two driver pickers + lap selector -->
	<div class="cmp__controls">
		<select class="cmp__select" style="border-color:{pick1 ? color1 : 'var(--brd)'}" bind:value={pick1}>
			<option value="">{$t('filter.select_driver')}</option>
			{#each allCodes as code}<option value={code} disabled={code === pick2}>{code} - {getTeam(code)}</option>{/each}
		</select>
		<span class="cmp__vs">{$t('charts.vs')}</span>
		<select class="cmp__select" style="border-color:{pick2 ? color2 : 'var(--brd)'}" bind:value={pick2}>
			<option value="">{$t('filter.select_driver')}</option>
			{#each allCodes as code}<option value={code} disabled={code === pick1}>{code} - {getTeam(code)}</option>{/each}
		</select>
		{#if ready}
			<div class="cmp__lap-picker">
				<span class="cmp__lap-label">{$t('tooltip.lap')}</span>
				<select class="cmp__lap-select" bind:value={selectedLap}>
					{#each lapOptions as lap}<option value={lap}>{lap}</option>{/each}
				</select>
			</div>
		{/if}
	</div>

	{#if ready}
		<!-- Overview Cards -->
		{#if stats}
		<div class="cmp__stats">
			<div class="cmp__stat cmp__stat--accent">
				<span class="cmp__stat-label">{$t('charts.best_lap')}</span>
				<div class="cmp__stat-row">
					<div><span class="cmp__stat-code" style="color:{color1}">{pick1}</span><span class="cmp__stat-big" style="color:{color1}">{formatTime(stats.best1)}</span></div>
					<div><span class="cmp__stat-code" style="color:{color2}">{pick2}</span><span class="cmp__stat-big" style="color:{color2}">{formatTime(stats.best2)}</span></div>
				</div>
			</div>
			<div class="cmp__stat">
				<span class="cmp__stat-label">{$t('charts.avg_pace')}</span>
				<div class="cmp__stat-row">
					<div><span class="cmp__stat-code" style="color:{color1}">{pick1}</span><span class="cmp__stat-big" style="color:{color1}">{formatTime(stats.avg1)}</span></div>
					<div><span class="cmp__stat-code" style="color:{color2}">{pick2}</span><span class="cmp__stat-big" style="color:{color2}">{formatTime(stats.avg2)}</span></div>
				</div>
			</div>
			<div class="cmp__stat">
				<span class="cmp__stat-label">D/C</span>
				<div class="cmp__stat-row">
					<div><span class="cmp__stat-code" style="color:{color1}">{pick1}</span><span class="cmp__stat-big" style="color:{color1}">{stats.dc1?.toFixed(2) ?? '-'}</span></div>
					<div><span class="cmp__stat-code" style="color:{color2}">{pick2}</span><span class="cmp__stat-big" style="color:{color2}">{stats.dc2?.toFixed(2) ?? '-'}</span></div>
				</div>
			</div>
		</div>

		<!-- Sector Cards -->
		<div class="cmp__sectors">
			{#each [['S1', stats.s1_1, stats.s1_2], ['S2', stats.s2_1, stats.s2_2], ['S3', stats.s3_1, stats.s3_2]] as [label, v1, v2]}
				{@const delta = (v1 != null && v2 != null) ? v1 - v2 : null}
				{@const winner = delta != null ? (delta < 0 ? pick1 : pick2) : null}
				<div class="cmp__sec" style="border-left-color:{winner ? teamColor(winner) : 'var(--brd)'}">
					<span class="cmp__sec-label">{label}</span>
					<div class="cmp__sec-row"><span style="color:{color1}">{pick1}</span><span class:cmp__best={delta != null && delta < 0}>{v1 != null ? v1.toFixed(3) + 's' : '-'}</span></div>
					<div class="cmp__sec-row"><span style="color:{color2}">{pick2}</span><span class:cmp__best={delta != null && delta > 0}>{v2 != null ? v2.toFixed(3) + 's' : '-'}</span></div>
					{#if delta != null}<span class="cmp__sec-delta" style="color:{teamColor(winner)}">{delta > 0 ? '+' : ''}{delta.toFixed(3)}s</span>{/if}
				</div>
			{/each}
		</div>
		{/if}

		<!-- Compare Charts (custom components, no store deps) -->
		<CompareSpeedTrace {raceId} driver1={pick1} driver2={pick2} {color1} {color2} {selectedLap} {circuit} totalLaps={raceInfo.total_laps || 58} />
		<CompareTrackMap {raceId} drivers={[...driverList.filter(d => d.driver === pick1), ...driverList.filter(d => d.driver === pick2), ...driverList.filter(d => d.driver !== pick1 && d.driver !== pick2)]} {circuit} totalLaps={raceInfo?.total_laps || 58} compareDriver1={pick1} compareDriver2={pick2} {selectedLap} />
		<CompareEnergyTimeline {raceId} driver1={pick1} driver2={pick2} {color1} {color2} />
	{:else}
		<div class="cmp__empty">
			<p>{$t('charts.select_drivers')}</p>
		</div>
	{/if}
</div>

<style>
	.cmp {
		position: fixed; inset: 0; z-index: 200;
		overflow-y: auto; background: #0F1117; color: #E8E8ED;
		font-family: 'DM Sans', sans-serif; -webkit-font-smoothing: antialiased;
		padding: 1.5rem 2rem 3rem;
		--fh: 'Space Grotesk', sans-serif; --fm: 'JetBrains Mono', monospace;
		--ac: #E24B4A; --bg2: #1A1D27; --bgc: #22252F; --brd: #2E3240; --tm: #6B7280;
	}
	.cmp :global(*) { border-radius: 0 !important; }

	.cmp__header { margin-bottom: 1.25rem; }
	.cmp__back { font-family: var(--fm); font-size: 11px; color: var(--ac); text-decoration: none; letter-spacing: .08em; }
	.cmp__back:hover { text-decoration: none; opacity: .8; }
	.cmp__title { font-family: var(--fh); font-size: 28px; font-weight: 700; text-transform: uppercase; margin-top: .5rem; }

	/* Controls bar */
	.cmp__controls { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.75rem; flex-wrap: wrap; }
	.cmp__select { font-family: var(--fm); font-size: 13px; background: #0F1117; color: #E8E8ED; border: 2px solid var(--brd); padding: 10px 14px; cursor: pointer; min-width: 200px; transition: border-color .2s; }
	.cmp__select:focus { outline: none; border-color: var(--ac); }
	.cmp__vs { font-family: var(--fh); font-size: 18px; color: var(--tm); }
	.cmp__lap-picker { display: flex; align-items: center; gap: .5rem; margin-left: auto; }
	.cmp__lap-label { font-family: var(--fm); font-size: 10px; color: var(--tm); text-transform: uppercase; letter-spacing: .1em; }
	.cmp__lap-select { font-family: var(--fm); font-size: 13px; background: #0F1117; color: #E8E8ED; border: 1px solid var(--brd); padding: 8px 12px; cursor: pointer; min-width: 70px; }

	/* Stats */
	.cmp__stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px; margin-bottom: 1.5rem; }
	.cmp__stat { background: var(--bg2); padding: 1.3rem 1.5rem; border-left: 3px solid var(--brd); transition: border-color .2s; }
	.cmp__stat:hover { border-left-color: var(--ac); }
	.cmp__stat--accent { border-left-color: var(--ac); background: linear-gradient(135deg, var(--bg2) 0%, rgba(226,75,74,.06) 100%); }
	.cmp__stat-label { font-family: var(--fm); font-size: 10px; color: var(--tm); text-transform: uppercase; letter-spacing: .1em; display: block; margin-bottom: .75rem; }
	.cmp__stat-row { display: flex; justify-content: space-between; gap: .75rem; }
	.cmp__stat-row > div { display: flex; flex-direction: column; gap: 2px; }
	.cmp__stat-code { font-family: var(--fm); font-size: 10px; font-weight: 700; }
	.cmp__stat-big { font-family: var(--fh); font-size: 22px; font-weight: 700; line-height: 1; }

	/* Sectors */
	.cmp__sectors { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px; margin-bottom: 1.5rem; }
	.cmp__sec { background: var(--bg2); padding: 1.2rem 1.4rem; border-left: 3px solid var(--brd); }
	.cmp__sec-label { font-family: var(--fh); font-size: 20px; font-weight: 700; display: block; margin-bottom: .75rem; }
	.cmp__sec-row { display: flex; justify-content: space-between; font-family: var(--fm); font-size: 14px; margin-bottom: .3rem; }
	.cmp__best { color: #22C55E !important; font-weight: 700; }
	.cmp__sec-delta { display: block; margin-top: .4rem; font-family: var(--fm); font-size: 12px; font-weight: 700; }

	.cmp__empty { display: flex; align-items: center; justify-content: center; min-height: 300px; font-family: var(--fm); font-size: 14px; color: var(--tm); }

	@media (max-width: 900px) {
		.cmp__stats, .cmp__sectors { grid-template-columns: 1fr; }
		.cmp__controls { flex-direction: column; align-items: stretch; }
		.cmp__select { min-width: auto; }
		.cmp__lap-picker { margin-left: 0; }
		.cmp { padding: 1rem; }
	}
</style>
