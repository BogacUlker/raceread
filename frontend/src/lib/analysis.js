/**
 * Data-derived race insights, computed client-side from the laps / strategy /
 * traffic payloads. Everything here is pure arithmetic on verified data, so
 * the moments it produces skip the fact-check gate that AI text requires.
 */

/** Cumulative race time per driver per lap; drivers with missing times get nulls after the gap. */
function cumTimes(laps) {
	const out = {};
	for (const d of laps) {
		let cum = 0;
		let broken = false;
		const m = {};
		for (const l of [...(d.laps || [])].sort((a, b) => a.lap - b.lap)) {
			if (broken || l.time_s == null) { broken = true; continue; }
			cum += l.time_s;
			m[l.lap] = cum;
		}
		out[d.driver] = m;
	}
	return out;
}

function posMap(laps) {
	const out = {};
	for (const d of laps) {
		const m = {};
		for (const l of d.laps || []) if (l.position != null) m[l.lap] = l.position;
		out[d.driver] = m;
	}
	return out;
}

/**
 * Undercut / overcut outcomes around pit cycles.
 * For every pair (A pits at L, rival B within 3.5s pits 1-4 laps later),
 * compare the gap one lap before A's stop with the gap one lap after B's.
 * Positive gain = the earlier stopper (A) won the cycle.
 */
export function computeUndercuts(laps, strategy, vscLaps = [], scLaps = []) {
	const neutralized = new Set([...vscLaps, ...scLaps]);
	const cums = cumTimes(laps);
	const pos = posMap(laps);
	const pits = {};
	for (const d of strategy?.drivers || []) pits[d.driver] = d.pit_laps || [];
	const results = [];
	const drivers = Object.keys(pits);
	for (const a of drivers) {
		for (const L of pits[a]) {
			for (const b of drivers) {
				if (b === a) continue;
				const M = (pits[b] || []).find((x) => x > L && x <= L + 4);
				if (!M) continue;
				// a stop under (V)SC distorts the cycle - that's not an undercut
				let touched = false;
				for (let k = L - 1; k <= M + 1; k++) if (neutralized.has(k)) touched = true;
				if (touched) continue;
				const before = cums[a]?.[L - 1] != null && cums[b]?.[L - 1] != null ? cums[a][L - 1] - cums[b][L - 1] : null;
				const S = M + 1;
				const after = cums[a]?.[S] != null && cums[b]?.[S] != null ? cums[a][S] - cums[b][S] : null;
				if (before == null || after == null) continue;
				if (Math.abs(before) > 3.5) continue; // not actually racing each other
				const gain = before - after; // positive: A gained on B
				if (Math.abs(gain) < 1.0) continue;
				const passed = (pos[a]?.[L - 1] > pos[b]?.[L - 1]) && (pos[a]?.[S + 1] < pos[b]?.[S + 1]);
				results.push({
					first: a, second: b, lap: L, rivalLap: M,
					gain: Math.round(gain * 10) / 10, passed,
				});
			}
		}
	}
	// keep the clearest cycle per pair
	const best = {};
	for (const r of results) {
		const k = [r.first, r.second].sort().join('-') + ':' + r.lap;
		if (!best[k] || Math.abs(r.gain) > Math.abs(best[k].gain)) best[k] = r;
	}
	return Object.values(best).sort((x, y) => Math.abs(y.gain) - Math.abs(x.gain));
}

/**
 * Sustained close-range battles from the traffic analysis payload.
 * (era-neutral: DRS died with the 2026 regs; the metric is simply gap < ~1s)
 * A battle = >= minLaps consecutive laps in traffic behind the same car.
 */
export function computeBattles(traffic, laps, strategy, minLaps = 6) {
	if (!traffic?.drivers) return [];
	const pos = posMap(laps);
	const pits = {};
	for (const d of strategy?.drivers || []) pits[d.driver] = new Set(d.pit_laps || []);
	const posToDriver = {};
	for (const [drv, m] of Object.entries(pos)) {
		for (const [lap, p] of Object.entries(m)) {
			(posToDriver[lap] ??= {})[p] = drv;
		}
	}
	const ahead = (drv, lap) => {
		const p = pos[drv]?.[lap];
		return p > 1 ? posToDriver[lap]?.[p - 1] : null;
	};
	const battles = [];
	for (const t of traffic.drivers) {
		const details = (t.lap_details || []).filter((x) => x.in_traffic);
		let run = [];
		const flush = () => {
			if (run.length >= minLaps) {
				const from = run[0], to = run[run.length - 1];
				const target = ahead(t.driver, from);
				const endLap = to + 1;
				let resolution = 'stuck';
				if (pits[t.driver]?.has(to) || pits[t.driver]?.has(endLap)) resolution = 'pit';
				else if (pos[t.driver]?.[endLap + 1] != null && pos[target]?.[endLap + 1] != null
					&& pos[t.driver][endLap + 1] < pos[target][endLap + 1]) resolution = 'passed';
				battles.push({ driver: t.driver, target, from, to, laps: run.length, resolution });
			}
			run = [];
		};
		let prevAhead = null;
		for (const d of (t.lap_details || [])) {
			const a = d.in_traffic ? ahead(t.driver, d.lap) : null;
			if (d.in_traffic && a && a === prevAhead && run.length && d.lap === run[run.length - 1] + 1) {
				run.push(d.lap);
			} else {
				flush();
				if (d.in_traffic && a) { run = [d.lap]; }
				prevAhead = a;
			}
		}
		flush();
	}
	return battles.filter((b) => b.target).sort((x, y) => y.laps - x.laps);
}

/** Annotation-shaped moments from undercuts + battles, for KeyMoments. */
export function derivedMoments(undercuts, battles) {
	const out = [];
	for (const u of undercuts.slice(0, 2)) {
		const [winner, loser, kind] = u.gain > 0 ? [u.first, u.second, 'under'] : [u.second, u.first, 'over'];
		const g = Math.abs(u.gain).toFixed(1);
		out.push({
			driver: winner, lap: u.lap, chart_type: 'strategy', severity: 'medium', derived: true,
			text_en: kind === 'under'
				? `${winner} pitted on lap ${u.lap} and gained ${g}s on ${loser} through the stop cycle - the undercut worked.`
				: `${winner} stayed out past ${loser}'s lap-${u.lap} stop and came out ${g}s ahead - the overcut paid off.`,
			text_tr: kind === 'under'
				? `${winner} ${u.lap}. turda pite girdi ve pit çevriminde ${loser}'a karşı ${g}s kazandı - undercut işledi.`
				: `${winner} ${loser}'ın ${u.lap}. turdaki pitine rağmen dışarıda kaldı ve çevrimden ${g}s önde çıktı - overcut işledi.`,
		});
	}
	for (const b of battles.slice(0, 2)) {
		const range = `${b.from}-${b.to}`;
		out.push({
			driver: b.driver, lap: b.from, chart_type: 'traffic', severity: 'medium', derived: true,
			text_en: b.resolution === 'passed'
				? `${b.driver} spent ${b.laps} laps within striking range of ${b.target} (laps ${range}) and finally made the move stick.`
				: b.resolution === 'pit'
					? `${b.driver} sat ${b.laps} laps behind ${b.target} (laps ${range}) before the team broke the stalemate with a pit call.`
					: `${b.driver} spent ${b.laps} laps within a second of ${b.target} (laps ${range}) but couldn't find a way past.`,
			text_tr: b.resolution === 'passed'
				? `${b.driver}, ${b.laps} tur boyunca ${b.target}'ı kovaladı (tur ${range}) ve sonunda geçişi yapıştırdı.`
				: b.resolution === 'pit'
					? `${b.driver}, ${b.laps} tur ${b.target}'ın arkasında kaldı (tur ${range}); kilidi pit hamlesi çözdü.`
					: `${b.driver}, ${b.laps} tur boyunca ${b.target}'ın bir saniyelik menzilinde kaldı (tur ${range}) ama geçemedi.`,
		});
	}
	return out;
}

/** Consistency ranking: std dev of clean-lap times (lower = more metronomic). */
export function metronomScores(laps, vscLaps = [], scLaps = []) {
	const excluded = new Set([...vscLaps, ...scLaps]);
	const rows = [];
	for (const d of laps) {
		const clean = (d.laps || []).filter(
			(l) => l.time_s != null && l.is_accurate !== false && l.lap > 1 && !excluded.has(l.lap)
		).map((l) => l.time_s);
		if (clean.length < 10) continue;
		const mean = clean.reduce((s, v) => s + v, 0) / clean.length;
		const sd = Math.sqrt(clean.reduce((s, v) => s + (v - mean) ** 2, 0) / clean.length);
		rows.push({ driver: d.driver, team: d.team, sd: Math.round(sd * 1000) / 1000, n: clean.length });
	}
	return rows.sort((a, b) => a.sd - b.sd);
}

/** Top speeds at the four measurement points. */
export function speedTraps(laps) {
	const points = { speed_st: [], speed_i1: [], speed_i2: [], speed_fl: [] };
	for (const d of laps) {
		const best = {};
		for (const l of d.laps || []) {
			for (const k of Object.keys(points)) {
				if (l[k] != null && (!best[k] || l[k] > best[k].v)) best[k] = { v: l[k], lap: l.lap };
			}
		}
		for (const k of Object.keys(points)) {
			if (best[k]) points[k].push({ driver: d.driver, team: d.team, v: best[k].v, lap: best[k].lap });
		}
	}
	for (const k of Object.keys(points)) points[k].sort((a, b) => b.v - a.v);
	return points;
}
