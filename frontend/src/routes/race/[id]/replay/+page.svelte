<script>
	import { onMount } from 'svelte';
	import { flip } from 'svelte/animate';
	import { t, locale } from '$lib/i18n/index.js';
	import { TEAM_COLORS, localizedRaceName } from '$lib/constants.js';
	import { favoriteDriver } from '$lib/stores/prefs.js';

	let { data } = $props();
	let raceId = $derived(data.raceId);
	let raceInfo = $derived(data.raceInfo);
	let totalLaps = $derived(raceInfo.total_laps || 58);
	let vscLaps = $derived(data.vscData?.vsc_laps || []);
	let scLaps = $derived(data.vscData?.sc_laps || []);

	// ---- per-driver race model: cumulative time, position, last lap ----
	let model = $derived.by(() => {
		const out = {};
		for (const d of data.laps) {
			const posByLap = {};
			const cumByLap = {};
			let cum = 0;
			let ok = true;
			let lastLap = 0;
			for (const l of d.laps) {
				if (l.position != null) posByLap[l.lap] = l.position;
				if (ok && l.time_s != null) {
					cum += l.time_s;
					cumByLap[l.lap] = cum;
				} else if (l.time_s == null) {
					ok = false; // missing time: stop cumulative tracking (gaps become approximate)
				}
				lastLap = Math.max(lastLap, l.lap);
			}
			out[d.driver] = { team: d.team, posByLap, cumByLap, lastLap };
		}
		return out;
	});
	let drivers = $derived(Object.keys(model));

	// leader cumulative time per lap
	let leaderCum = $derived.by(() => {
		const lc = {};
		for (let L = 1; L <= totalLaps; L++) {
			let best = null;
			for (const c of Object.values(model)) {
				const v = c.cumByLap[L];
				if (v != null && (best === null || v < best)) best = v;
			}
			lc[L] = best;
		}
		return lc;
	});

	// ---- current lap + playback ----
	let lap = $state(1);
	onMount(() => {
		lap = Math.min(Math.max(1, data.startLap), raceInfo.total_laps || 58);
	});
	let playing = $state(false);
	let speed = $state(1);
	$effect(() => {
		if (!playing) return;
		const id = setInterval(() => {
			if (lap >= totalLaps) { playing = false; return; }
			lap = lap + 1;
		}, 900 / speed);
		return () => clearInterval(id);
	});

	// ---- running order at current lap ----
	let order = $derived.by(() => {
		const rows = [];
		for (const [drv, m] of Object.entries(model)) {
			if (m.lastLap < Math.min(lap, totalLaps) && m.lastLap < totalLaps * 0.96) {
				// retired before this point
				if (m.lastLap < lap) { rows.push({ drv, team: m.team, out: true, pos: 900 + (99 - m.lastLap), gapText: $t('replay.out') }); continue; }
			}
			const cLap = Math.min(lap, m.lastLap);
			const pos = m.posByLap[cLap] ?? 99;
			const lapsDown = lap - cLap;
			let gapText;
			if (pos === 1 && lapsDown === 0) gapText = $t('replay.leader');
			else if (lapsDown >= 1) gapText = '+' + lapsDown + 'L';
			else {
				const g = m.cumByLap[lap] != null && leaderCum[lap] != null ? m.cumByLap[lap] - leaderCum[lap] : null;
				gapText = g == null ? '—' : '+' + g.toFixed(1);
			}
			const prevPos = m.posByLap[Math.max(1, cLap - 1)] ?? pos;
			rows.push({ drv, team: m.team, out: false, pos: pos + lapsDown * 0.001, gapText, delta: prevPos - pos });
		}
		rows.sort((a, b) => a.pos - b.pos);
		return rows;
	});

	// ---- gap chart geometry ----
	const W = 820, H = 380, ML = 40, MR = 56, MT = 12, MB = 30;
	let series = $derived.by(() => {
		const out = [];
		const seenTeam = new Set();
		for (const [drv, m] of Object.entries(model)) {
			const pts = [];
			for (let L = 1; L <= m.lastLap; L++) {
				const c = m.cumByLap[L], lc = leaderCum[L];
				if (c == null || lc == null) break;
				pts.push([L, c - lc]);
			}
			if (pts.length > 1) {
				out.push({ drv, team: m.team, pts, dashed: seenTeam.has(m.team) });
				seenTeam.add(m.team);
			}
		}
		return out;
	});
	let maxGap = $derived.by(() => {
		let mx = 30;
		for (const s of series) {
			const finalPos = model[s.drv].posByLap[model[s.drv].lastLap] ?? 99;
			if (finalPos <= 10) mx = Math.max(mx, ...s.pts.map((p) => p[1]));
		}
		return Math.min(mx * 1.05, 120);
	});
	function gx(L) { return ML + ((L - 1) / Math.max(1, totalLaps - 1)) * (W - ML - MR); }
	function gy(gap) { return MT + Math.min(1, gap / maxGap) * (H - MT - MB); }
	function pathFor(s) {
		return s.pts.map((p, i) => (i === 0 ? 'M' : 'L') + gx(p[0]).toFixed(1) + ',' + gy(p[1]).toFixed(1)).join('');
	}
	let hovered = $state(null);
	function lineOpacity(s) {
		if (hovered) return hovered === s.drv ? 1 : 0.1;
		if ($favoriteDriver === s.drv) return 1;
		const finalPos = model[s.drv].posByLap[model[s.drv].lastLap] ?? 99;
		return finalPos <= 6 ? 0.85 : 0.22;
	}

	// pit density per lap for the scrubber markers
	let pitLapCounts = $derived.by(() => {
		const c = {};
		for (const d of data.strategy?.drivers || []) {
			for (const pl of d.pit_laps || []) c[pl] = (c[pl] || 0) + 1;
		}
		return c;
	});

	function tc(team) { return TEAM_COLORS[team] || '#888'; }
	function gpName(name) {
		if (!name) return '';
		const n = localizedRaceName(name, $locale);
		const parts = n.split('Grand Prix');
		if (parts.length === 2) return parts[0].toLocaleUpperCase($locale === 'tr' ? 'tr' : 'en') + 'GRAND PRIX';
		return n.toUpperCase();
	}
	function handleKey(e) {
		if (e.key === 'ArrowRight') lap = Math.min(totalLaps, lap + 1);
		if (e.key === 'ArrowLeft') lap = Math.max(1, lap - 1);
		if (e.key === ' ') { e.preventDefault(); playing = !playing; }
	}
</script>

<svelte:head>
	<title>Replay - {raceInfo.name} - RaceRead</title>
</svelte:head>
<svelte:window onkeydown={handleKey} />

<div class="rp">
	<div class="rp__header">
		<a href="/race/{raceId}" class="rp__back">&larr; {gpName(raceInfo.name)}</a>
		<h1 class="rp__title">{$t('replay.room_title')}</h1>
		<p class="rp__sub">{raceInfo.circuit} &middot; {raceInfo.date}</p>
	</div>

	<!-- Controls + scrubber -->
	<div class="rp__controls">
		<button class="rp__play" onclick={() => playing = !playing} aria-label={playing ? $t('replay.pause') : $t('replay.play')}>
			{playing ? '❚❚' : '▶'}
		</button>
		<span class="rp__lapno">{$t('replay.lap')} <b>{lap}</b> / {totalLaps}</span>
		<div class="rp__speeds">
			{#each [1, 2, 4] as s}
				<button class:on={speed === s} onclick={() => speed = s}>{s}x</button>
			{/each}
		</div>
	</div>
	<div class="rp__scrub">
		<svg viewBox="0 0 {W} 22" class="rp__marks" preserveAspectRatio="none" aria-hidden="true">
			{#each vscLaps as vl}<rect x={gx(vl) - 3} y="0" width="7" height="22" fill="#F59E0B" opacity="0.22" />{/each}
			{#each scLaps as sl}<rect x={gx(sl) - 3} y="0" width="7" height="22" fill="#E24B4A" opacity="0.25" />{/each}
			{#each Object.entries(pitLapCounts) as [pl, n]}
				<circle cx={gx(+pl)} cy="11" r={Math.min(4, 1.5 + n * 0.4)} fill="#7D8794" opacity="0.8" />
			{/each}
		</svg>
		<input type="range" min="1" max={totalLaps} bind:value={lap} class="rp__range" aria-label={$t('replay.lap')} />
	</div>

	<div class="rp__main">
		<!-- Running order -->
		<div class="rp__order">
			<span class="rp__colhead">{$t('replay.order')}</span>
			{#each order as row (row.drv)}
				<div class="rp__row" class:rp__row--out={row.out} class:rp__row--fav={$favoriteDriver === row.drv} animate:flip={{ duration: 280 }}>
					<span class="rp__pos">{row.out ? '-' : Math.floor(row.pos)}</span>
					<span class="rp__bar" style="background:{tc(row.team)}"></span>
					<span class="rp__code">{row.drv}</span>
					{#if !row.out && row.delta}
						<span class="rp__delta" class:up={row.delta > 0} class:down={row.delta < 0}>
							{row.delta > 0 ? '▲' : '▼'}{Math.abs(row.delta)}
						</span>
					{/if}
					<span class="rp__gap">{row.gapText}</span>
				</div>
			{/each}
		</div>

		<!-- Gap chart -->
		<div class="rp__chart">
			<span class="rp__colhead">{$t('replay.gaps')}</span>
			<svg viewBox="0 0 {W} {H}" class="rp__svg" role="img" aria-label={$t('replay.gaps')}>
				{#each [0, 0.25, 0.5, 0.75, 1] as f}
					<line x1={ML} x2={W - MR} y1={gy(maxGap * f)} y2={gy(maxGap * f)} stroke="#22252F" />
					<text x={ML - 6} y={gy(maxGap * f) + 3} text-anchor="end" class="rp__tick">{Math.round(maxGap * f)}s</text>
				{/each}
				{#each vscLaps as vl}<rect x={gx(vl) - 3} y={MT} width="7" height={H - MT - MB} fill="#F59E0B" opacity="0.06" />{/each}
				{#each scLaps as sl}<rect x={gx(sl) - 3} y={MT} width="7" height={H - MT - MB} fill="#E24B4A" opacity="0.07" />{/each}
				{#each series as s (s.drv)}
					<path d={pathFor(s)} fill="none" stroke={tc(s.team)} stroke-width={hovered === s.drv ? 2.6 : 1.6}
						stroke-dasharray={s.dashed ? '5 3' : 'none'} opacity={lineOpacity(s)} />
				{/each}
				<line x1={gx(lap)} x2={gx(lap)} y1={MT} y2={H - MB} stroke="#E8E8ED" stroke-width="1.2" opacity="0.7" />
				{#each series as s (s.drv)}
					{@const pt = s.pts.find((p) => p[0] === Math.min(lap, s.pts.at(-1)?.[0] ?? 1))}
					{#if pt && lineOpacity(s) > 0.5}
						<circle cx={gx(pt[0])} cy={gy(pt[1])} r="3.5" fill={tc(s.team)} />
					{/if}
				{/each}
				{#each Array.from({ length: Math.ceil(totalLaps / 10) }, (_, i) => (i + 1) * 10) as tick}
					{#if tick <= totalLaps}<text x={gx(tick)} y={H - 8} text-anchor="middle" class="rp__tick">L{tick}</text>{/if}
				{/each}
			</svg>
			<div class="rp__legend">
				{#each series.filter((s) => lineOpacity(s) >= 0.5 || true).slice(0, 22) as s (s.drv)}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<span class="rp__lg" onmouseenter={() => hovered = s.drv} onmouseleave={() => hovered = null}>
						<i style="background:{tc(s.team)}"></i>{s.drv}
					</span>
				{/each}
			</div>
		</div>
	</div>
</div>

<style>
	.rp {
		position: fixed; inset: 0; z-index: 200;
		overflow-y: auto; background: #0F1117; color: #E8E8ED;
		font-family: 'DM Sans', sans-serif; -webkit-font-smoothing: antialiased;
		padding: 1.5rem 2rem 3rem;
		--fm: 'JetBrains Mono', monospace; --fh: 'Space Grotesk', sans-serif;
		--brd: #2E3240; --bg2: #1A1D27; --tm: #7D8794; --ac: #E24B4A;
	}
	.rp :global(*) { border-radius: 0 !important; }
	.rp__header { margin-bottom: 1rem; }
	.rp__back { font-family: var(--fm); font-size: 11px; color: var(--ac); text-decoration: none; letter-spacing: .08em; }
	.rp__back:hover { text-decoration: none; opacity: .8; }
	.rp__title { font-family: var(--fh); font-size: 28px; font-weight: 700; text-transform: uppercase; margin-top: .5rem; }
	.rp__sub { font-family: var(--fm); font-size: 10px; color: var(--tm); letter-spacing: .1em; text-transform: uppercase; margin-top: 2px; }

	.rp__controls { display: flex; align-items: center; gap: 14px; margin-bottom: 4px; }
	.rp__play { width: 38px; height: 38px; background: var(--ac); color: #fff; border: none; font-size: 13px; cursor: pointer; }
	.rp__play:hover { background: #C93B3A; }
	.rp__lapno { font-family: var(--fm); font-size: 13px; color: #9CA3AF; }
	.rp__lapno b { color: #E8E8ED; font-size: 16px; }
	.rp__speeds { display: flex; gap: 2px; }
	.rp__speeds button { font-family: var(--fm); font-size: 10px; padding: 4px 10px; background: none; border: 1px solid var(--brd); color: var(--tm); cursor: pointer; }
	.rp__speeds button.on { color: #E8E8ED; background: var(--bg2); }

	.rp__scrub { position: relative; margin-bottom: 1.25rem; }
	.rp__marks { width: 100%; height: 22px; display: block; }
	.rp__range { width: 100%; margin: 0; accent-color: #E24B4A; cursor: pointer; }

	.rp__main { display: grid; grid-template-columns: 250px 1fr; gap: 1.25rem; align-items: start; }
	.rp__colhead { display: block; font-family: var(--fm); font-size: 10px; color: var(--tm); letter-spacing: .12em; text-transform: uppercase; margin-bottom: 8px; }

	.rp__order { background: var(--bg2); padding: 12px 12px 8px; }
	.rp__row { display: flex; align-items: center; gap: 7px; padding: 4px 4px; font-family: var(--fm); font-size: 12px; }
	.rp__row--out { opacity: .3; }
	.rp__row--fav { background: rgba(245,158,11,.07); }
	.rp__pos { width: 20px; text-align: right; color: var(--tm); font-variant-numeric: tabular-nums; }
	.rp__bar { width: 3px; height: 13px; flex-shrink: 0; }
	.rp__code { font-weight: 700; width: 38px; }
	.rp__delta { font-size: 9px; }
	.rp__delta.up { color: #22C55E; }
	.rp__delta.down { color: #E24B4A; }
	.rp__gap { margin-left: auto; color: #9CA3AF; font-variant-numeric: tabular-nums; font-size: 11px; }

	.rp__chart { background: var(--bg2); padding: 12px 14px; }
	.rp__svg { width: 100%; height: auto; display: block; }
	.rp__tick { font-family: var(--fm); font-size: 9px; fill: var(--tm); }
	.rp__legend { display: flex; flex-wrap: wrap; gap: 8px 12px; margin-top: 8px; }
	.rp__lg { display: inline-flex; align-items: center; gap: 4px; font-family: var(--fm); font-size: 10px; color: #9CA3AF; cursor: default; }
	.rp__lg i { width: 8px; height: 8px; display: inline-block; }

	@media (max-width: 900px) {
		.rp { padding: 1rem; }
		.rp__main { grid-template-columns: 1fr; }
	}
	@media (prefers-reduced-motion: reduce) {
		.rp__row { transition: none !important; }
	}
</style>
