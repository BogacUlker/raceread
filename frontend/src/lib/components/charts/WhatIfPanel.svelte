<!--
	What-if simulator - counterfactual pit strategy for one driver.
	The other 19 drivers replay reality; SC/VSC stay as they happened.

	Model, all fitted from this race's own data:
	  predicted(lap) = driverBase + fuel(lap) + tireDeg(compound, age)
	                   [+ pit loss on stop laps, + traffic penalty when the
	                    sim timeline falls within close range of a real car]
	Neutralized (SC/VSC) laps reuse the driver's actual recorded times.
-->
<script>
	import { t, locale } from '$lib/i18n/index.js';
	import { COMPOUND_COLORS, TEAM_COLORS } from '$lib/constants.js';

	let { laps = [], strategy = null, raceInfo = null, vscLaps = [], scLaps = [], teamsMap = {}, traffic = null } = $props();

	const FUEL = 0.055; // s per lap of fuel burn (typical, era-insensitive enough for V1)
	let totalLaps = $derived(raceInfo?.total_laps || 0);
	let neutral = $derived(new Set([...vscLaps, ...scLaps]));

	// ---- shared race model (independent of picked driver) ----
	let race = $derived.by(() => {
		const mid = totalLaps / 2;
		const times = {}; // driver -> lap -> time
		const cums = {}; // driver -> lap -> cum (reality)
		const finishers = [];
		for (const d of laps) {
			const m = {};
			for (const l of d.laps || []) if (l.time_s != null) m[l.lap] = l.time_s;
			times[d.driver] = m;
			let c = 0;
			const cm = {};
			for (let L = 1; L <= totalLaps; L++) { if (m[L] == null) { break; } c += m[L]; cm[L] = c; }
			cums[d.driver] = cm;
			if (cm[totalLaps] != null) finishers.push(d.driver);
		}
		// driver clean fuel-corrected base
		const base = {};
		const cleanResiduals = []; // {compound, age, r}
		const stintOf = {}; // driver -> lap -> {compound, age}
		for (const s of strategy?.drivers || []) {
			const m = {};
			for (const st of s.stints || []) {
				for (let L = st.start_lap; L <= st.end_lap; L++) m[L] = { compound: st.compound, age: L - st.start_lap + 1 };
			}
			stintOf[s.driver] = m;
		}
		for (const d of laps) {
			const clean = (d.laps || []).filter((l) => l.time_s != null && l.is_accurate !== false && l.lap > 1 && !neutral.has(l.lap));
			if (clean.length < 8) continue;
			const corr = clean.map((l) => l.time_s + FUEL * (l.lap - mid)).sort((a, b) => a - b);
			base[d.driver] = corr[Math.floor(corr.length / 2)];
			for (const l of clean) {
				const st = stintOf[d.driver]?.[l.lap];
				if (!st) continue;
				const r = l.time_s + FUEL * (l.lap - mid) - base[d.driver];
				if (Math.abs(r) < 4) cleanResiduals.push({ compound: st.compound, age: st.age, r });
			}
		}
		// compound deg tables: median residual per age, linearly extended past data
		const deg = {};
		for (const c of [...new Set(cleanResiduals.map((x) => x.compound))]) {
			const byAge = {};
			for (const x of cleanResiduals) if (x.compound === c) (byAge[x.age] ??= []).push(x.r);
			const pts = Object.entries(byAge)
				.filter(([, v]) => v.length >= 2)
				.map(([a, v]) => [+a, v.sort((p, q) => p - q)[Math.floor(v.length / 2)]])
				.sort((p, q) => p[0] - q[0]);
			if (pts.length >= 4) deg[c] = pts;
		}
		const degAt = (c, age) => {
			const pts = deg[c];
			if (!pts) return null;
			if (age <= pts[0][0]) return pts[0][1];
			for (let i = 1; i < pts.length; i++) {
				if (age <= pts[i][0]) {
					const [a0, v0] = pts[i - 1], [a1, v1] = pts[i];
					return v0 + (v1 - v0) * (age - a0) / Math.max(1, a1 - a0);
				}
			}
			// extrapolate from the tail slope (flagged in UI via extrapolated())
			const [a0, v0] = pts[Math.max(0, pts.length - 4)], [a1, v1] = pts[pts.length - 1];
			const slope = (v1 - v0) / Math.max(1, a1 - a0);
			return v1 + slope * (age - a1);
		};
		const maxAge = {};
		for (const [c, pts] of Object.entries(deg)) maxAge[c] = pts[pts.length - 1][0];
		// measured pit loss (green-flag stops)
		const losses = [];
		for (const s of strategy?.drivers || []) {
			for (const p of s.pit_laps || []) {
				if (neutral.has(p) || neutral.has(p + 1)) continue;
				const tin = times[s.driver]?.[p], tout = times[s.driver]?.[p + 1], b = base[s.driver];
				if (tin == null || tout == null || b == null) continue;
				const loss = tin + tout - 2 * (b - FUEL * (mid - p));
				if (loss > 5 && loss < 60) losses.push(loss);
			}
		}
		losses.sort((a, b) => a - b);
		const pitLoss = losses.length ? losses[Math.floor(losses.length / 2)] : 21;
		// per-lap traffic penalty measured by the traffic analysis
		let trafficPen = 0.3;
		const degs = (traffic?.drivers || []).map((x) => x.pace_degradation).filter((v) => v != null && v > 0 && v < 2);
		if (degs.length >= 4) { degs.sort((a, b) => a - b); trafficPen = degs[Math.floor(degs.length / 2)]; }
		return { mid, times, cums, finishers, base, degAt, maxAge, compounds: Object.keys(deg), pitLoss, trafficPen };
	});

	// ---- driver + editable strategy state ----
	let driver = $state('');
	let simStints = $state([]); // [{compound, from, to}]
	$effect(() => {
		if (!driver || !race.finishers.includes(driver)) driver = race.finishers[0] || '';
	});
	let actualStints = $derived.by(() => {
		const s = (strategy?.drivers || []).find((x) => x.driver === driver);
		return (s?.stints || []).map((st) => ({ compound: st.compound, from: st.start_lap, to: st.end_lap }));
	});
	$effect(() => { simStints = actualStints.map((s) => ({ ...s })); });
	let dirty = $derived(JSON.stringify(simStints) !== JSON.stringify(actualStints));

	function movePit(i, newLap) {
		const s = simStints.map((x) => ({ ...x }));
		const lo = s[i].from + 2, hi = s[i + 1].to - 2;
		const L = Math.max(lo, Math.min(hi, newLap));
		s[i].to = L; s[i + 1].from = L + 1;
		simStints = s;
	}
	function cycleCompound(i) {
		const opts = race.compounds;
		if (opts.length < 2) return;
		const s = simStints.map((x) => ({ ...x }));
		s[i].compound = opts[(opts.indexOf(s[i].compound) + 1) % opts.length];
		simStints = s;
	}
	function addStop() {
		if (simStints.length >= 4) return;
		const s = simStints.map((x) => ({ ...x }));
		let bi = 0;
		for (let i = 1; i < s.length; i++) if (s[i].to - s[i].from > s[bi].to - s[bi].from) bi = i;
		const st = s[bi], midL = Math.floor((st.from + st.to) / 2);
		if (midL - st.from < 3 || st.to - midL < 3) return;
		s.splice(bi, 1, { ...st, to: midL }, { compound: st.compound, from: midL + 1, to: st.to });
		simStints = s;
	}
	function removeStop() {
		if (simStints.length <= 1) return;
		const s = simStints.map((x) => ({ ...x }));
		const merged = { compound: s[s.length - 2].compound, from: s[s.length - 2].from, to: s[s.length - 1].to };
		s.splice(s.length - 2, 2, merged);
		simStints = s;
	}
	function reset() { simStints = actualStints.map((s) => ({ ...s })); }

	// ---- simulation ----
	// Model bias cancels by differencing: the edited strategy is compared
	// against a baseline simulation of the ACTUAL strategy, not raw reality.
	function simulate(stints) {
		const stintAt = (L) => stints.find((s) => L >= s.from && L <= s.to);
		const pitSet = new Set(stints.slice(0, -1).map((s) => s.to));
		let cum = 0;
		const cums = [];
		let extrapolated = false;
		let trafficNote = null;
		let trafficLaps = 0;
		for (let L = 1; L <= totalLaps; L++) {
			const st = stintAt(L);
			const act = race.times[driver]?.[L];
			let tSim;
			if (L === 1 || neutral.has(L) || !st) {
				tSim = act ?? race.base[driver];
				if (pitSet.has(L)) tSim = (act ?? race.base[driver]) + race.pitLoss * (neutral.has(L) ? 0.5 : 1);
			} else {
				const d = race.degAt(st.compound, L - st.from + 1);
				if (d == null) { tSim = act ?? race.base[driver]; }
				else {
					if (L - st.from + 1 > (race.maxAge[st.compound] || 99)) extrapolated = true;
					tSim = race.base[driver] - FUEL * (race.mid - L) + d;
					if (pitSet.has(L)) tSim += race.pitLoss;
				}
			}
			cum += tSim;
			if (L > 2 && !neutral.has(L)) {
				for (const [rv, rc] of Object.entries(race.cums)) {
					if (rv === driver || rc[L] == null) continue;
					const gap = cum - rc[L];
					if (gap > 0 && gap < 1.8) {
						cum += race.trafficPen;
						trafficLaps++;
						if (!trafficNote) trafficNote = { lap: L, rival: rv };
						break;
					}
				}
			}
			cums.push(cum);
		}
		return { total: cum, cums, extrapolated, trafficNote, trafficLaps };
	}

	let sim = $derived.by(() => {
		if (!driver || !simStints.length || !actualStints.length || !race.base[driver]) return null;
		const actTotal = race.cums[driver]?.[totalLaps];
		if (actTotal == null) return null;
		const baseline = simulate(actualStints);
		const edited = simulate(simStints);
		const gain = baseline.total - edited.total; // positive = edited strategy faster
		let changed = 0;
		for (let L = 1; L <= totalLaps; L++) {
			const a = actualStints.find((s) => L >= s.from && L <= s.to);
			const b = simStints.find((s) => L >= s.from && L <= s.to);
			if (a && b && (a.compound !== b.compound || (L - a.from) !== (L - b.from))) changed++;
		}
		const band = Math.min(8, Math.max(1.5, changed * 0.09));
		const predictedTotal = actTotal - gain;
		const rivals = race.finishers.filter((d) => d !== driver).map((d) => race.cums[d][totalLaps]);
		const rank = (total) => 1 + rivals.filter((v) => v < total).length;
		const deltas = edited.cums.map((c, i) => [i + 1, c - baseline.cums[i]]);
		return {
			gain, band,
			pos: rank(predictedTotal),
			posLo: rank(predictedTotal - band), posHi: rank(predictedTotal + band),
			actualPos: rank(actTotal),
			deltas,
			extrapolated: edited.extrapolated,
			trafficNote: edited.trafficNote, trafficLaps: edited.trafficLaps,
		};
	});

	// ---- chart geometry ----
	let width = $state(800);
	const H = 150, PAD = { l: 44, r: 14, t: 12, b: 22 };
	let chart = $derived.by(() => {
		if (!sim) return null;
		const vals = sim.deltas.filter(([, v]) => v != null).map(([, v]) => v);
		if (!vals.length) return null;
		const lo = Math.min(...vals, -1), hi = Math.max(...vals, 1);
		const x = (L) => PAD.l + (L - 1) / Math.max(1, totalLaps - 1) * (width - PAD.l - PAD.r);
		const y = (v) => PAD.t + (1 - (v - lo) / (hi - lo)) * (H - PAD.t - PAD.b);
		const path = sim.deltas.filter(([, v]) => v != null).map(([L, v], i) => (i ? 'L' : 'M') + x(L).toFixed(1) + ',' + y(v).toFixed(1)).join('');
		return { x, y, path, zero: y(0), lo, hi };
	});

	function tc(code) { return TEAM_COLORS[teamsMap[code]] || 'var(--text-muted)'; }
	function cc(c) { return COMPOUND_COLORS[c] || 'var(--text-secondary)'; }
	let pitSliders = $derived(simStints.slice(0, -1).map((s, i) => ({ i, lap: s.to, min: simStints[i].from + 2, max: simStints[i + 1].to - 2 })));
</script>

{#if race.finishers.length && race.compounds.length}
	<div class="wip" bind:clientWidth={width}>
		<div class="wip__bar">
			<span class="wip__title">{$t('whatif.title')}</span>
			<select bind:value={driver} class="wip__select" style="border-color:{tc(driver)}" aria-label={$t('filter.select_driver')}>
				{#each race.finishers as d}<option value={d}>{d}</option>{/each}
			</select>
			<span class="wip__hint">{$t('whatif.hint')}</span>
			<div class="wip__actions">
				<button class="wip__btn" onclick={addStop} disabled={simStints.length >= 4}>+ {$t('whatif.stop')}</button>
				<button class="wip__btn" onclick={removeStop} disabled={simStints.length <= 1}>&minus; {$t('whatif.stop')}</button>
				<button class="wip__btn" class:wip__btn--on={dirty} onclick={reset} disabled={!dirty}>&#8634; {$t('whatif.reset')}</button>
			</div>
		</div>

		<!-- editable stint strip -->
		<div class="wip__strip">
			{#each simStints as s, i}
				<button
					class="wip__stint" style="flex:{s.to - s.from + 1}; background:{cc(s.compound)}"
					onclick={() => cycleCompound(i)} title={$t('whatif.cycle')}
				>{s.compound[0]}<span class="wip__stlaps">{s.to - s.from + 1}</span></button>
				{#if i < simStints.length - 1}<span class="wip__pitmark"></span>{/if}
			{/each}
		</div>
		{#each pitSliders as p (p.i)}
			<div class="wip__sliderrow">
				<span class="wip__pl">{$t('whatif.pit')} {p.i + 1} &middot; L{p.lap}</span>
				<input type="range" min={p.min} max={p.max} value={p.lap} oninput={(e) => movePit(p.i, +e.target.value)} aria-label="{$t('whatif.pit')} {p.i + 1}" />
			</div>
		{/each}

		{#if sim && chart}
			<svg viewBox="0 0 {width} {H}" width="100%" height={H} class="wip__chart" role="img" aria-label={$t('whatif.chart')}>
				<line x1={PAD.l} y1={chart.zero} x2={width - PAD.r} y2={chart.zero} stroke="#4A4F5E" stroke-width="1" stroke-dasharray="4,4" />
				<text x={width - PAD.r} y={chart.zero - 5} fill="var(--text-muted)" font-size="9" text-anchor="end" font-family="var(--font-mono)">{$t('whatif.reality')}</text>
				<path d={chart.path} fill="none" stroke={tc(driver)} stroke-width="2.2" />
				{#each simStints.slice(0, -1) as s}
					<line x1={chart.x(s.to)} y1={PAD.t} x2={chart.x(s.to)} y2={H - PAD.b} stroke="var(--text-primary)" stroke-width="1" opacity=".25" />
				{/each}
				<text x={PAD.l - 6} y={chart.y(chart.lo) - 2} fill="var(--text-muted)" font-size="9" text-anchor="end" font-family="var(--font-mono)">{chart.lo > 0 ? '+' : ''}{chart.lo.toFixed(0)}s</text>
				<text x={PAD.l - 6} y={chart.y(chart.hi) + 8} fill="var(--text-muted)" font-size="9" text-anchor="end" font-family="var(--font-mono)">{chart.hi > 0 ? '+' : ''}{chart.hi.toFixed(0)}s</text>
			</svg>
			<p class="wip__chartnote">{$t('whatif.chart_note')}</p>

			<div class="wip__verdict">
				<div class="wip__v">
					<span class="k">{$t('whatif.predicted')}</span>
					<span class="v" class:up={sim.pos < sim.actualPos} class:down={sim.pos > sim.actualPos}>
						P{sim.pos}{#if sim.pos !== sim.actualPos}<small> &larr; P{sim.actualPos}</small>{/if}
					</span>
					<span class="s">{sim.posLo !== sim.posHi ? `${$t('whatif.band')}: P${sim.posLo}-P${sim.posHi}` : $t('whatif.band_solid')}</span>
				</div>
				<div class="wip__v">
					<span class="k">{$t('whatif.gain')}</span>
					<span class="v" class:up={sim.gain > 0} class:down={sim.gain < 0}>{sim.gain > 0 ? '+' : ''}{sim.gain.toFixed(1)}s</span>
					<span class="s">&plusmn;{sim.band.toFixed(1)}s {$t('whatif.uncertainty')}</span>
				</div>
				<div class="wip__v">
					<span class="k">{$t('whatif.critical')}</span>
					<span class="v v--text">
						{#if !dirty}
							{$t('whatif.untouched')}
						{:else if sim.trafficNote}
							{$locale === 'tr'
								? `L${sim.trafficNote.lap}'de ${sim.trafficNote.rival} trafiğine düşer (${sim.trafficLaps} tur, +${(sim.trafficLaps * race.trafficPen).toFixed(1)}s)`
								: `Falls into ${sim.trafficNote.rival}'s traffic on L${sim.trafficNote.lap} (${sim.trafficLaps} laps, +${(sim.trafficLaps * race.trafficPen).toFixed(1)}s)`}
						{:else}
							{$t('whatif.clean_air')}
						{/if}
					</span>
				</div>
			</div>

			<p class="wip__assump">
				{$t('whatif.assumptions')}: {$t('whatif.a_base')} &middot; {$t('whatif.a_pit')} {race.pitLoss.toFixed(1)}s &middot; {$t('whatif.a_traffic')} {race.trafficPen.toFixed(2)}s &middot; {$t('whatif.a_sc')}{#if sim.extrapolated} &middot; <b class="wip__warn">{$t('whatif.a_extrap')} ?!</b>{/if}
			</p>
		{/if}
	</div>
{/if}

<style>
	.wip { background: var(--bg-secondary); border: 1px solid var(--border); border-left: 3px solid var(--accent); padding: 16px 18px; margin-top: 12px; }
	.wip__bar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
	.wip__title { font-family: var(--font-heading); font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }
	.wip__select { background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border); font-family: var(--font-mono); font-size: 11px; padding: 5px 8px; cursor: pointer; }
	.wip__hint { font-family: var(--font-mono); font-size: 9.5px; color: var(--text-muted); }
	.wip__actions { margin-left: auto; display: flex; gap: 6px; }
	.wip__btn { font-family: var(--font-mono); font-size: 10px; padding: 5px 10px; background: none; border: 1px solid var(--border); color: var(--text-muted); cursor: pointer; }
	.wip__btn:hover:not(:disabled) { color: var(--text-primary); border-color: #6B7280; }
	.wip__btn:disabled { opacity: .35; cursor: default; }
	.wip__btn--on { color: var(--accent); border-color: rgba(226,75,74,.5); }
	.wip__strip { display: flex; align-items: center; height: 30px; margin-bottom: 8px; }
	.wip__stint { height: 100%; display: flex; align-items: center; justify-content: center; gap: 6px; border: none; cursor: pointer; font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--bg-secondary); }
	.wip__stint:hover { filter: brightness(1.12); }
	.wip__stlaps { font-size: 9px; font-weight: 500; opacity: .75; }
	.wip__pitmark { width: 4px; height: 38px; background: var(--text-primary); flex: 0 0 4px; }
	.wip__sliderrow { display: grid; grid-template-columns: 90px 1fr; gap: 12px; align-items: center; margin-bottom: 4px; }
	.wip__pl { font-family: var(--font-mono); font-size: 10px; color: var(--text-secondary); }
	.wip__sliderrow input { accent-color: var(--accent); cursor: pointer; margin: 0; }
	.wip__chart { display: block; margin-top: 10px; background: var(--bg-primary); border: 1px solid var(--border); }
	.wip__chartnote { margin: 4px 0 0; font-family: var(--font-mono); font-size: 9px; color: var(--text-muted); }
	.wip__verdict { display: grid; grid-template-columns: 1fr 1fr 1.4fr; gap: 2px; margin-top: 12px; }
	@media (max-width: 768px) { .wip__verdict { grid-template-columns: 1fr; } }
	.wip__v { background: var(--bg-primary); padding: 12px 14px; }
	.wip__v .k { display: block; font-family: var(--font-mono); font-size: 9px; letter-spacing: .1em; text-transform: uppercase; color: var(--text-muted); }
	.wip__v .v { display: block; font-family: var(--font-heading); font-size: 22px; font-weight: 700; margin-top: 2px; }
	.wip__v .v small { font-size: 13px; color: var(--text-muted); font-weight: 500; }
	.wip__v .v--text { font-size: 12.5px; line-height: 1.5; font-family: var(--font-body, 'DM Sans'), sans-serif; font-weight: 500; }
	.wip__v .s { display: block; font-family: var(--font-mono); font-size: 9.5px; color: var(--text-muted); margin-top: 3px; }
	.up { color: #22C55E; } .down { color: var(--accent); }
	.wip__assump { margin: 12px 0 0; font-family: var(--font-mono); font-size: 9px; color: var(--text-muted); line-height: 1.7; text-transform: uppercase; letter-spacing: .04em; }
	.wip__warn { color: #F59E0B; }
</style>
