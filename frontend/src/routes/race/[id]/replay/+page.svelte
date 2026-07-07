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

	// ---- broadcast tower extras: tyre at lap, pit tag, fastest-so-far ----
	let stintMap = $derived.by(() => {
		const m = {};
		for (const d of data.strategy?.drivers || []) {
			m[d.driver] = { stints: d.stints || [], pits: new Set(d.pit_laps || []) };
		}
		return m;
	});
	function tyreAt(drv, L) {
		const st = (stintMap[drv]?.stints || []).find((x) => L >= x.start_lap && L <= x.end_lap);
		return st?.compound?.[0] || null;
	}
	const COMPOUND_RING = { S: '#FF3333', M: '#FFC300', H: '#F0F0F0', I: '#39B54A', W: '#0067FF' };
	function inPit(drv, L) { const p = stintMap[drv]?.pits; return p ? (p.has(L) || p.has(L - 1)) : false; }
	// holder of the fastest lap set so far (broadcast purple)
	let fastestSoFar = $derived.by(() => {
		let best = null;
		for (const d of data.laps) {
			for (const l of d.laps || []) {
				if (l.lap > lap || l.time_s == null || l.is_accurate === false || l.lap <= 1) continue;
				if (!best || l.time_s < best.t) best = { drv: d.driver, t: l.time_s, lap: l.lap };
			}
		}
		return best;
	});
	function fmtFastest(t) { const m = Math.floor(t / 60); return m + ':' + (t - m * 60).toFixed(3).padStart(6, '0'); }
	// track status chip for the current lap
	let trackStatus = $derived(
		scLaps.includes(lap) ? 'sc' : vscLaps.includes(lap) ? 'vsc' : 'green'
	);

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
			items.push({ kind: 'radio', lap: c.lap, driver: c.driver, url: c.url, segments: c.segments });
		}
		return items.sort((a, b) => a.lap - b.lap);
	});
	let feedVisible = $derived(feedAll.filter((i) => i.lap <= lap).slice(-9).reverse());
	let radioLaps = $derived([...new Set((data.radio?.clips || []).filter((c) => c.lap).map((c) => c.lap))]);


	// lap-1 start animation (lazy: telemetry loads when the panel opens)
	import StartAnimation from '$lib/components/StartAnimation.svelte';
	import RadioCard from '$lib/components/ui/RadioCard.svelte';
	let showStart = $state(false);
	let qualiPos = $derived.by(() => {
		const m = {};
		for (const d of data.qualifying?.drivers || []) { const g = d.grid_position ?? d.position; if (g != null) m[d.driver] = g; }
		return m;
	});
	function flagColor(i) {
		if (i.category === 'SafetyCar') return 'var(--accent)';
		if (i.flag === 'RED') return 'var(--accent)';
		if (i.flag === 'YELLOW' || i.flag === 'DOUBLE YELLOW') return '#F59E0B';
		if (i.flag === 'GREEN') return '#22C55E';
		if (i.flag === 'CHEQUERED') return 'var(--text-primary)';
		return 'var(--text-muted)';
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
		<span class="rp__lapchip"><b>{$t('replay.lap').toLocaleUpperCase($locale === 'tr' ? 'tr' : 'en')}</b><span>{lap}</span><small>/ {totalLaps}</small></span>
		<span class="rp__status rp__status--{trackStatus}">
			{trackStatus === 'sc' ? 'SAFETY CAR' : trackStatus === 'vsc' ? 'VSC' : $t('replay.track_clear')}
		</span>
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
			{#each scLaps as sl}<rect x={gx(sl) - 3} y="0" width="7" height="22" fill="var(--accent)" opacity="0.25" />{/each}
			{#each radioLaps as rl}<circle cx={gx(rl)} cy="4" r="2.5" fill="#6C98FF" opacity="0.9" />{/each}
			{#each Object.entries(pitLapCounts) as [pl, n]}
				<circle cx={gx(+pl)} cy="11" r={Math.min(4, 1.5 + n * 0.4)} fill="var(--text-muted)" opacity="0.8" />
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
				<div class="rp__trow" class:rp__trow--out={row.out} class:rp__trow--up={row.delta > 0} class:rp__trow--fav={$favoriteDriver === row.drv} class:rp__trow--lead={!row.out && Math.floor(row.pos) === 1} animate:flip={{ duration: 280 }}>
					<span class="rp__tpos">{row.out ? '-' : Math.floor(row.pos)}</span>
					<span class="rp__tbar" style="background:{tc(row.team)}"></span>
					<span class="rp__ttla">{row.drv}</span>
					<span class="rp__ttag">{#if !row.out && inPit(row.drv, lap)}<b>PIT</b>{/if}</span>
					<span class="rp__tgap" class:rp__tgap--pur={fastestSoFar?.drv === row.drv && !row.out}>{row.gapText}</span>
					<span class="rp__ttyre">
						{#if !row.out && tyreAt(row.drv, Math.min(lap, totalLaps))}
							{@const c = tyreAt(row.drv, Math.min(lap, totalLaps))}
							<i style="border-color:{COMPOUND_RING[c] || '#999'}">{c}</i>
						{/if}
					</span>
				</div>
			{/each}
			{#if fastestSoFar}
				<div class="rp__fastest">⏱ {fastestSoFar.drv} {fmtFastest(fastestSoFar.t)} <small>L{fastestSoFar.lap}</small></div>
			{/if}
			{#if order.some((r) => r.gapText?.startsWith('~'))}
				<p class="rp__note">~ {$t('replay.approx')}</p>
			{/if}
		</div>

		<!-- Gap chart -->
		<div class="rp__chart">
			<span class="rp__colhead">{$t('replay.gaps')}</span>
			<svg viewBox="0 0 {W} {H}" class="rp__svg" role="img" aria-label={$t('replay.gaps')}>
				{#each [0, 0.25, 0.5, 0.75, 1] as f}
					<line x1={ML} x2={W - MR} y1={gy(maxGap * f)} y2={gy(maxGap * f)} stroke="var(--bg-card)" />
					<text x={ML - 6} y={gy(maxGap * f) + 3} text-anchor="end" class="rp__tick">{Math.round(maxGap * f)}s</text>
				{/each}
				{#each vscLaps as vl}<rect x={gx(vl) - 3} y={MT} width="7" height={H - MT - MB} fill="#F59E0B" opacity="0.06" />{/each}
				{#each scLaps as sl}<rect x={gx(sl) - 3} y={MT} width="7" height={H - MT - MB} fill="var(--accent)" opacity="0.07" />{/each}
				{#each series as s (s.drv)}
					<path d={pathFor(s)} fill="none" stroke={tc(s.team)} stroke-width={hovered === s.drv ? 2.6 : 1.6}
						stroke-dasharray={s.dashed ? '5 3' : 'none'} opacity={lineOpacity(s)} />
				{/each}
				<line x1={gx(Math.min(lapFloat, totalLaps))} x2={gx(Math.min(lapFloat, totalLaps))} y1={MT} y2={H - MB} stroke="var(--text-primary)" stroke-width="1.2" opacity="0.7" />
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
								<RadioCard clip={item} team={teamsMap[item.driver]} lap={item.lap} compact />
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
		overflow-y: auto; background: var(--bg-primary); color: var(--text-primary);
		font-family: var(--font-body); -webkit-font-smoothing: antialiased;
		padding: 1.5rem 2rem 3rem;
		--fm: var(--font-mono); --fh: var(--font-heading);
		--brd: var(--border); --bg2: var(--bg-secondary); --tm: var(--text-muted); --ac: var(--accent);
	}
	.rp :global(*) { border-radius: 0 !important; }
	.rp__header { margin-bottom: 1rem; }
	.rp__back { font-family: var(--fm); font-size: 11px; color: var(--ac-text, var(--accent-text)); text-decoration: none; letter-spacing: .08em; }
	.rp__back:hover { text-decoration: none; opacity: .8; }
	.rp__title { font-family: var(--fh); font-size: 28px; font-weight: 700; text-transform: uppercase; margin-top: .5rem; }
	.rp__sub { font-family: var(--fm); font-size: 10px; color: var(--tm); letter-spacing: .1em; text-transform: uppercase; margin-top: 2px; }

	.rp__controls { display: flex; align-items: center; gap: 14px; margin-bottom: 4px; }
	.rp__play { width: 38px; height: 38px; background: var(--ac); color: #fff; border: none; font-size: 13px; cursor: pointer; }
	.rp__play:hover { background: #C93B3A; }
	.rp__lapchip { display: inline-flex; align-items: stretch; white-space: nowrap; }
	.rp__lapchip b { background: var(--accent); color: #fff; font-family: var(--font-heading); font-weight: 900; font-style: italic; font-size: 11px; padding: 5px 10px; letter-spacing: .05em; }
	.rp__lapchip span { background: rgba(0,0,0,.75); color: #fff; font-weight: 800; font-size: 14px; padding: 3px 6px 3px 10px; display: flex; align-items: center; }
	.rp__lapchip small { background: rgba(0,0,0,.75); color: var(--text-muted); font-weight: 600; font-size: 10px; padding-right: 10px; display: flex; align-items: center; }
	.rp__status { font-family: var(--font-heading); font-weight: 800; font-style: italic; font-size: 10px; letter-spacing: .08em; padding: 4px 12px; border: 1px solid; white-space: nowrap; align-self: center; }
	.rp__status--green { color: var(--timing-pb); border-color: rgba(0,196,106,.45); background: rgba(0,196,106,.1); }
	.rp__status--vsc { color: var(--timing-caution); border-color: rgba(255,216,0,.45); background: rgba(255,216,0,.08); animation: rp-glow-y 1.2s infinite; }
	.rp__status--sc { color: var(--accent-text); border-color: rgba(225,6,0,.5); background: rgba(225,6,0,.12); animation: rc-pulse 1.2s infinite; }
	@keyframes rp-glow-r { 50% { box-shadow: 0 0 14px rgba(225,6,0,.55); } }
	@keyframes rp-glow-y { 50% { box-shadow: 0 0 14px rgba(255,216,0,.4); } }
	.rp__speeds { display: flex; gap: 2px; }
	.rp__speeds button { font-family: var(--fm); font-size: 10px; padding: 4px 10px; background: none; border: 1px solid var(--brd); color: var(--tm); cursor: pointer; }
	.rp__speeds button.on { color: var(--text-primary); background: var(--bg2); }
	.rp__startbtn { font-family: var(--fm); font-size: 10px; padding: 6px 12px; background: none; border: 1px solid var(--brd); color: var(--tm); cursor: pointer; letter-spacing: .06em; }
	.rp__startbtn:hover { color: var(--text-primary); border-color: #6B7280; }
	.rp__startbtn.on { color: var(--ac-text, var(--accent-text)); border-color: rgba(226,75,74,.5); }

	.rp__scrub { position: relative; margin-bottom: 1.25rem; }
	.rp__marks { width: 100%; height: 22px; display: block; }
	.rp__range { width: 100%; margin: 0; accent-color: var(--accent-text); cursor: pointer; }

	.rp__main { display: grid; grid-template-columns: 250px 1fr 270px; gap: 1.25rem; align-items: start; }
	@media (max-width: 1250px) { .rp__main { grid-template-columns: 250px 1fr; } .rp__feed { grid-column: 1 / -1; } }
	.rp__feed { background: var(--bg2); padding: 12px 14px; }
	.rp__feeditems { display: flex; flex-direction: column; gap: 8px; max-height: 420px; overflow-y: auto; }
	.rp__fi { display: flex; align-items: baseline; gap: 8px; font-family: var(--fm); font-size: 10.5px; line-height: 1.45; }
	.rp__fi--new { animation: rp-flash 1.2s ease-out; }
	@keyframes rp-flash { 0% { background: rgba(226,75,74,.18); } 100% { background: transparent; } }
	.rp__fi-lap { color: var(--tm); font-size: 9.5px; flex: 0 0 26px; }
	.rp__fi-dot { width: 6px; height: 6px; flex: 0 0 6px; align-self: center; }
	.rp__fi-text { color: #C6CAD3; }
	.rp__fi-empty { color: var(--tm); font-size: 10.5px; font-family: var(--fm); }
	@media (prefers-reduced-motion: reduce) { .rp__fi--new { animation: none; } }
	.rp__colhead { display: inline-block; font-family: var(--font-heading); font-weight: 900; font-style: italic; font-size: 10px; color: #fff; background: var(--accent); letter-spacing: .08em; text-transform: uppercase; margin-bottom: 10px; padding: 3px 10px; }

	.rp__order { background: var(--bg2); padding: 12px 10px 8px; }
	.rp__trow { display: grid; grid-template-columns: 26px 6px 44px 26px 1fr 26px; align-items: stretch; height: 26px; margin-bottom: 2px; background: var(--bg-card); }
	.rp__trow--out .rp__tbar, .rp__trow--out .rp__ttyre, .rp__trow--out .rp__tpos { opacity: .3; }
	.rp__trow--out .rp__ttla, .rp__trow--out .rp__tgap { color: var(--text-muted); }
	.rp__trow--fav { outline: 1px solid rgba(245,158,11,.35); }
	.rp__trow--lead .rp__tpos { background: var(--accent); }
	.rp__trow--up { animation: rp-up 1.4s ease-out; }
	@keyframes rp-up { 0% { background: rgba(0,196,106,.4); } 100% { background: var(--bg-card); } }
	.rp__tpos { font-family: var(--font-varsity); color: #fff; font-size: 11.5px; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,.07); }
	.rp__tbar { }
	.rp__ttla { font-family: var(--font-heading); font-weight: 800; font-size: 12.5px; letter-spacing: .05em; display: flex; align-items: center; padding-left: 8px; }
	.rp__ttag { display: flex; align-items: center; }
	.rp__ttag b { font-size: 8.5px; font-weight: 900; background: #fff; color: #111; padding: 1.5px 4px; letter-spacing: .04em; }
	.rp__tgap { font-family: var(--fm); font-weight: 600; font-size: 12px; display: flex; align-items: center; justify-content: flex-end; color: #D6D9E0; font-variant-numeric: tabular-nums; padding-right: 2px; }
	.rp__tgap--pur { color: var(--timing-fastest-text); font-weight: 700; }
	.rp__ttyre { display: flex; align-items: center; justify-content: center; }
	.rp__ttyre i { width: 15px; height: 15px; border-radius: 50%; border: 2.5px solid; display: inline-flex; align-items: center; justify-content: center; font-style: normal; font-weight: 900; font-size: 8.5px; color: #fff; box-sizing: border-box; }
	.rp__fastest { margin-top: 8px; font-family: var(--fm); font-weight: 700; font-size: 11px; color: var(--timing-fastest-text); letter-spacing: .04em; }
	.rp__fastest small { color: var(--tm); }
	.rp__note { font-family: var(--fm); font-size: 9.5px; color: var(--tm); margin-top: 6px; }

	.rp__chart { background: var(--bg2); padding: 12px 14px; }
	.rp__svg { width: 100%; height: auto; display: block; }
	.rp__tick { font-family: var(--fm); font-size: 9.5px; fill: var(--tm); }
	.rp__legend { display: flex; flex-wrap: wrap; gap: 8px 12px; margin-top: 8px; }
	.rp__lg { display: inline-flex; align-items: center; gap: 4px; font-family: var(--fm); font-size: 10px; color: var(--text-secondary); cursor: default; }
	.rp__lg i { width: 8px; height: 8px; display: inline-block; }

	@media (max-width: 900px) {
		.rp { padding: 1rem; }
		.rp__main { grid-template-columns: 1fr; }
	}
	@media (prefers-reduced-motion: reduce) {
		.rp__trow { transition: none !important; animation: none !important; }
	}
</style>
