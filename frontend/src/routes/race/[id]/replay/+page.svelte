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
		// median lap time per lap: fills missing times (red flags, SC glitches)
		// so gaps stay computable; affected gaps are marked approximate
		const byLap = {};
		for (const d of data.laps) {
			for (const l of d.laps) {
				if (l.time_s != null) (byLap[l.lap] ??= []).push(l.time_s);
			}
		}
		const medByLap = {};
		for (const [L, arr] of Object.entries(byLap)) {
			arr.sort((a, b) => a - b);
			medByLap[L] = arr[Math.floor(arr.length / 2)];
		}
		// red-flag laps have no timed driver at all: fill with the race-wide
		// median so cum times keep advancing (cancels out in gap subtraction)
		const allT = Object.values(byLap).flat().sort((a, b) => a - b);
		const globalMed = allT.length ? allT[Math.floor(allT.length / 2)] : null;
		const out = {};
		for (const d of data.laps) {
			const posByLap = {};
			const cumByLap = {};
			let cum = 0;
			let lastLap = 0;
			let approxFrom = null;
			for (const l of [...d.laps].sort((a, b) => a.lap - b.lap)) {
				if (l.position != null) posByLap[l.lap] = l.position;
				const raceWideGap = !byLap[l.lap]?.length;
				const t = l.time_s ?? medByLap[l.lap] ?? globalMed;
				if (t != null) {
					cum += t;
					cumByLap[l.lap] = cum;
					// a race-wide gap shifts everyone equally, so it does not
					// make this driver's gaps approximate from here on
					if (l.time_s == null && !raceWideGap && approxFrom === null) approxFrom = l.lap;
				}
				lastLap = Math.max(lastLap, l.lap);
			}
			out[d.driver] = { team: d.team, posByLap, cumByLap, lastLap, approxFrom };
		}
		return out;
	});
	let drivers = $derived(Object.keys(model));

	// laps where no driver has a time (red flag): gaps there are approximate
	let raceWideFillLaps = $derived.by(() => {
		const timed = new Set();
		for (const d of data.laps) for (const l of d.laps) if (l.time_s != null) timed.add(l.lap);
		const s = new Set();
		for (const d of data.laps) for (const l of d.laps) if (!timed.has(l.lap)) s.add(l.lap);
		return s;
	});

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

	// ---- current lap + playback (continuous: lapFloat drives the cursor,
	// integer lap drives the running order) ----
	let lapFloat = $state(1);
	let lap = $derived(Math.max(1, Math.min(totalLaps, Math.floor(lapFloat))));
	onMount(() => {
		lapFloat = Math.min(Math.max(1, data.startLap), raceInfo.total_laps || 58);
	});
	let playing = $state(false);
	let speed = $state(1);
	$effect(() => {
		if (!playing) return;
		let raf;
		let prev = performance.now();
		const step = (now) => {
			const dt = (now - prev) / 1000;
			prev = now;
			lapFloat = Math.min(totalLaps, lapFloat + (dt / 0.9) * speed);
			if (lapFloat >= totalLaps) { playing = false; return; }
			raf = requestAnimationFrame(step);
		};
		raf = requestAnimationFrame(step);
		return () => cancelAnimationFrame(raf);
	});

	// interpolated gap for smooth cursor dots
	function gapAt(s, lf) {
		const i = Math.min(s.pts.length - 1, Math.max(0, Math.floor(lf) - 1));
		const j = Math.min(s.pts.length - 1, i + 1);
		const a = s.pts[i], b = s.pts[j];
		if (!a) return null;
		const f = Math.min(1, Math.max(0, lf - a[0]));
		return a[1] + (b[1] - a[1]) * f;
	}

	let teamsMap = $derived(Object.fromEntries(data.laps.map((d) => [d.driver, d.team])));

	// ---- race control + radio feed ----
	// FIA messages and radio clips merged on the lap axis; blue flags and
	// sector-clear spam are dropped so the feed reads like a broadcast ticker.
	let feedAll = $derived.by(() => {
		const items = [];
		for (const m of data.rcFeed?.messages || []) {
			if (!m.lap || m.lap < 1 || m.lap > totalLaps) continue;
			if (m.flag === 'BLUE' || m.flag === 'CLEAR') continue;
			let text = (m.message || '').replace(/^FIA STEWARDS: /, '').replace(/\s*\(?\d{2}:\d{2}:\d{2}\)?\s*$/, '');
			if (text.length > 110) text = text.slice(0, 107) + '...';
			items.push({ kind: 'rc', lap: m.lap, text, flag: m.flag, category: m.category });
		}
		for (const c of data.radio?.clips || []) {
			if (!c.lap || c.lap < 1 || c.lap > totalLaps) continue;
			items.push({ kind: 'radio', lap: c.lap, driver: c.driver, url: c.url });
		}
		return items.sort((a, b) => a.lap - b.lap);
	});
	let feedVisible = $derived(feedAll.filter((i) => i.lap <= lap).slice(-9).reverse());
	let radioLaps = $derived([...new Set((data.radio?.clips || []).filter((c) => c.lap).map((c) => c.lap))]);

	let playingUrl = $state(null);
	let radioTime = $state({ cur: 0, dur: 0 });
	let audio = null;
	function toggleRadio(clip) {
		if (playingUrl === clip.url) { audio?.pause(); playingUrl = null; return; }
		audio?.pause();
		audio = new Audio(clip.url);
		audio.onended = () => { playingUrl = null; };
		audio.onerror = () => { playingUrl = null; };
		audio.ontimeupdate = () => { radioTime = { cur: audio.currentTime, dur: audio.duration || 0 }; };
		audio.play().catch(() => { playingUrl = null; });
		radioTime = { cur: 0, dur: 0 };
		playingUrl = clip.url;
	}
	function mmss(t) { return Math.floor(t / 60) + ':' + String(Math.floor(t % 60)).padStart(2, '0'); }

	// lap-1 start animation (lazy: telemetry loads when the panel opens)
	import StartAnimation from '$lib/components/StartAnimation.svelte';
	let showStart = $state(false);
	let qualiPos = $derived.by(() => {
		const m = {};
		for (const d of data.qualifying?.drivers || []) { const g = d.grid_position ?? d.position; if (g != null) m[d.driver] = g; }
		return m;
	});
	function flagColor(i) {
		if (i.category === 'SafetyCar') return '#E24B4A';
		if (i.flag === 'RED') return '#E24B4A';
		if (i.flag === 'YELLOW' || i.flag === 'DOUBLE YELLOW') return '#F59E0B';
		if (i.flag === 'GREEN') return '#22C55E';
		if (i.flag === 'CHEQUERED') return '#E8E8ED';
		return '#7D8794';
	}

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
				const approx = (m.approxFrom !== null && lap >= m.approxFrom) || raceWideFillLaps.has(lap);
				gapText = g == null ? '—' : (approx ? '~' : '+') + g.toFixed(1);
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
		if (e.key === 'ArrowRight') lapFloat = Math.min(totalLaps, Math.floor(lapFloat) + 1);
		if (e.key === 'ArrowLeft') lapFloat = Math.max(1, Math.floor(lapFloat) - 1);
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
		<button class="rp__startbtn" class:on={showStart} onclick={() => { showStart = !showStart; playing = false; }}>
			🏁 {$t('replay.start_title')}
		</button>
	</div>
	<div class="rp__scrub">
		<svg viewBox="0 0 {W} 22" class="rp__marks" preserveAspectRatio="none" aria-hidden="true">
			{#each vscLaps as vl}<rect x={gx(vl) - 3} y="0" width="7" height="22" fill="#F59E0B" opacity="0.22" />{/each}
			{#each scLaps as sl}<rect x={gx(sl) - 3} y="0" width="7" height="22" fill="#E24B4A" opacity="0.25" />{/each}
			{#each radioLaps as rl}<circle cx={gx(rl)} cy="4" r="2.5" fill="#6C98FF" opacity="0.9" />{/each}
			{#each Object.entries(pitLapCounts) as [pl, n]}
				<circle cx={gx(+pl)} cy="11" r={Math.min(4, 1.5 + n * 0.4)} fill="#7D8794" opacity="0.8" />
			{/each}
		</svg>
		<input type="range" min="1" max={totalLaps} value={lap} oninput={(e) => { lapFloat = +e.target.value; }} class="rp__range" aria-label={$t('replay.lap')} />
	</div>

	{#if showStart}
		<StartAnimation {raceId} {teamsMap} circuit={data.circuit} {qualiPos} />
	{/if}

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
			{#if order.some((r) => r.gapText?.startsWith('~'))}
				<p class="rp__note">~ {$t('replay.approx')}</p>
			{/if}
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
				<line x1={gx(Math.min(lapFloat, totalLaps))} x2={gx(Math.min(lapFloat, totalLaps))} y1={MT} y2={H - MB} stroke="#E8E8ED" stroke-width="1.2" opacity="0.7" />
				{#each series as s (s.drv)}
					{@const lf = Math.min(lapFloat, s.pts.at(-1)?.[0] ?? 1)}
					{@const g = gapAt(s, lf)}
					{#if g != null && lineOpacity(s) > 0.5}
						<circle cx={gx(lf)} cy={gy(g)} r="3.5" fill={tc(s.team)} />
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

		<!-- Race control + radio feed -->
		{#if feedAll.length}
			<div class="rp__feed">
				<span class="rp__colhead">{$t('replay.feed')}</span>
				<div class="rp__feeditems">
					{#each feedVisible as item (item.kind + item.lap + (item.url || item.text))}
						<div class="rp__fi" class:rp__fi--new={item.lap === lap}>
							<span class="rp__fi-lap">L{item.lap}</span>
							{#if item.kind === 'radio'}
								<button class="rp__fi-radio" onclick={() => toggleRadio(item)}>
									{playingUrl === item.url ? '■' : '▶'}
									<b style="color:{tc((data.laps.find((d) => d.driver === item.driver) || {}).team)}">{item.driver}</b>
									{playingUrl === item.url ? mmss(radioTime.cur) + (radioTime.dur ? ' / ' + mmss(radioTime.dur) : '') : $t('replay.radio')}
								</button>
							{:else}
								<span class="rp__fi-dot" style="background:{flagColor(item)}"></span>
								<span class="rp__fi-text">{item.text}</span>
							{/if}
						</div>
					{:else}
						<p class="rp__fi-empty">{$t('replay.feed_empty')}</p>
					{/each}
				</div>
			</div>
		{/if}
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
	.rp__startbtn { font-family: var(--fm); font-size: 10px; padding: 6px 12px; background: none; border: 1px solid var(--brd); color: var(--tm); cursor: pointer; letter-spacing: .06em; }
	.rp__startbtn:hover { color: #E8E8ED; border-color: #6B7280; }
	.rp__startbtn.on { color: var(--ac); border-color: rgba(226,75,74,.5); }

	.rp__scrub { position: relative; margin-bottom: 1.25rem; }
	.rp__marks { width: 100%; height: 22px; display: block; }
	.rp__range { width: 100%; margin: 0; accent-color: #E24B4A; cursor: pointer; }

	.rp__main { display: grid; grid-template-columns: 250px 1fr 270px; gap: 1.25rem; align-items: start; }
	@media (max-width: 1250px) { .rp__main { grid-template-columns: 250px 1fr; } .rp__feed { grid-column: 1 / -1; } }
	.rp__feed { background: var(--bg2); padding: 12px 14px; }
	.rp__feeditems { display: flex; flex-direction: column; gap: 8px; max-height: 420px; overflow-y: auto; }
	.rp__fi { display: flex; align-items: baseline; gap: 8px; font-family: var(--fm); font-size: 10.5px; line-height: 1.45; }
	.rp__fi--new { animation: rp-flash 1.2s ease-out; }
	@keyframes rp-flash { 0% { background: rgba(226,75,74,.18); } 100% { background: transparent; } }
	.rp__fi-lap { color: var(--tm); font-size: 9px; flex: 0 0 26px; }
	.rp__fi-dot { width: 6px; height: 6px; flex: 0 0 6px; align-self: center; }
	.rp__fi-text { color: #C6CAD3; }
	.rp__fi-radio { display: inline-flex; gap: 6px; align-items: baseline; background: none; border: 1px solid var(--brd); color: #9CA3AF; font-family: var(--fm); font-size: 10px; padding: 3px 8px; cursor: pointer; }
	.rp__fi-radio:hover { border-color: #6C98FF; color: #E8E8ED; }
	.rp__fi-radio b { font-weight: 700; }
	.rp__fi-empty { color: var(--tm); font-size: 10.5px; font-family: var(--fm); }
	@media (prefers-reduced-motion: reduce) { .rp__fi--new { animation: none; } }
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
	.rp__note { font-family: var(--fm); font-size: 9px; color: var(--tm); margin-top: 6px; }

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
