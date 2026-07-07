<!--
	Tire degradation - lap-time delta (vs each driver's own clean median,
	so car pace cancels out) against tire age, split by compound.
	Dots are individual laps; lines are per-compound medians per age.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { COMPOUND_COLORS } from '$lib/constants.js';

	let { laps = [], vscLaps = [], scLaps = [] } = $props();

	let width = $state(900);
	const H = 260, PAD = { l: 46, r: 16, t: 14, b: 34 };

	let model = $derived.by(() => {
		const excluded = new Set([...vscLaps, ...scLaps]);
		const pts = [];
		for (const d of laps) {
			const clean = (d.laps || []).filter(
				(l) => l.time_s != null && l.is_accurate !== false && l.lap > 1 && !excluded.has(l.lap)
			);
			if (clean.length < 8) continue;
			const times = clean.map((l) => l.time_s).sort((a, b) => a - b);
			const med = times[Math.floor(times.length / 2)];
			for (const l of clean) {
				if (l.tire_age == null || !l.compound) continue;
				const delta = l.time_s - med;
				if (Math.abs(delta) > 5) continue; // outliers (traffic chaos, damage)
				pts.push({ age: l.tire_age, delta, compound: l.compound });
			}
		}
		const compounds = [...new Set(pts.map((p) => p.compound))];
		const maxAge = Math.min(45, Math.max(10, ...pts.map((p) => p.age)));
		// per-compound median line by age
		const lines = {};
		for (const c of compounds) {
			const byAge = {};
			for (const p of pts) if (p.compound === c && p.age <= maxAge) (byAge[p.age] ??= []).push(p.delta);
			const line = [];
			for (const [age, arr] of Object.entries(byAge)) {
				if (arr.length < 3) continue;
				arr.sort((a, b) => a - b);
				line.push([+age, arr[Math.floor(arr.length / 2)]]);
			}
			line.sort((a, b) => a[0] - b[0]);
			if (line.length >= 4) lines[c] = line;
		}
		const deltas = pts.map((p) => p.delta);
		const lo = Math.max(-2.5, Math.min(...deltas, -0.5));
		const hi = Math.min(4, Math.max(...deltas, 1.5));
		return { pts: pts.filter((p) => p.age <= maxAge && p.delta >= lo && p.delta <= hi), lines, maxAge, lo, hi };
	});

	let x = $derived((age) => PAD.l + (age - 1) / (model.maxAge - 1) * (width - PAD.l - PAD.r));
	let y = $derived((delta) => PAD.t + (1 - (delta - model.lo) / (model.hi - model.lo)) * (H - PAD.t - PAD.b));

	function cc(compound) { return COMPOUND_COLORS[compound] || '#9CA3AF'; }
	let yTicks = $derived.by(() => {
		const ticks = [];
		for (let v = Math.ceil(model.lo); v <= Math.floor(model.hi); v++) ticks.push(v);
		return ticks;
	});
</script>

<div class="tdg" bind:clientWidth={width}>
	<div class="tdg__head">
		<span class="tdg__title">{$t('insights.tire_deg')}</span>
		<div class="tdg__legend">
			{#each Object.keys(model.lines) as c}
				<span class="tdg__lg"><i style="background:{cc(c)}"></i>{c}</span>
			{/each}
		</div>
	</div>
	<svg viewBox="0 0 {width} {H}" width="100%" height={H} role="img" aria-label={$t('insights.tire_deg')}>
		{#each yTicks as tick}
			<line x1={PAD.l} y1={y(tick)} x2={width - PAD.r} y2={y(tick)} stroke="#2E3240" stroke-width={tick === 0 ? 1.4 : 0.6} />
			<text x={PAD.l - 8} y={y(tick)} fill="#7D8794" font-size="10" text-anchor="end" dominant-baseline="middle" font-family="'JetBrains Mono', monospace">{tick > 0 ? '+' + tick : tick}s</text>
		{/each}
		{#each [1, 10, 20, 30, 40].filter((v) => v <= model.maxAge) as tick}
			<text x={x(tick)} y={H - 14} fill="#7D8794" font-size="10" text-anchor="middle" font-family="'JetBrains Mono', monospace">{tick}</text>
		{/each}
		<text x={(PAD.l + width - PAD.r) / 2} y={H - 2} fill="#7D8794" font-size="9" text-anchor="middle" font-family="'JetBrains Mono', monospace" letter-spacing="1">{$t('insights.tire_age')}</text>
		{#each model.pts as p}
			<circle cx={x(p.age)} cy={y(p.delta)} r="2" fill={cc(p.compound)} opacity="0.22" />
		{/each}
		{#each Object.entries(model.lines) as [c, line]}
			<polyline
				points={line.map(([age, d]) => `${x(age)},${y(d)}`).join(' ')}
				fill="none" stroke={cc(c)} stroke-width="2.2" stroke-linejoin="round"
			/>
		{/each}
	</svg>
	<p class="tdg__note">{$t('insights.tire_deg_note')}</p>
</div>

<style>
	.tdg { background: var(--bg-secondary, #1A1D27); border: 1px solid var(--border, #2E3240); padding: 16px 18px; margin-top: 12px; }
	.tdg__head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; flex-wrap: wrap; gap: 8px; }
	.tdg__title { font-family: var(--font-heading); font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }
	.tdg__legend { display: flex; gap: 12px; }
	.tdg__lg { display: inline-flex; align-items: center; gap: 5px; font-family: var(--font-mono); font-size: 9.5px; color: var(--text-secondary, #9CA3AF); }
	.tdg__lg i { width: 10px; height: 3px; display: inline-block; }
	.tdg__note { margin: 6px 0 0; font-size: 10.5px; color: var(--text-muted, #7D8794); }
</style>
