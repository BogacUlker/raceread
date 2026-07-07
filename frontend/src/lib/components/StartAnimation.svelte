<!--
	Lap-1 start animation - every car's real x/y telemetry replayed from
	lights-out. Lap 1 shares a common clock across the field, so dots move
	on true data, not interpolated gaps.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { api } from '$lib/api.js';
	import { TEAM_COLORS } from '$lib/constants.js';

	let { raceId, teamsMap = {}, circuit = null, qualiPos = {} } = $props();

	let traces = $state(null);
	let failed = $state(false);
	$effect(() => {
		const id = raceId;
		if (!id) return;
		api(`/api/races/${id}/start-traces`)
			.then((d) => { traces = d.drivers || []; })
			.catch(() => { failed = true; });
	});

	// clock
	let tNow = $state(0);
	let playing = $state(false);
	let speed = $state(1);
	let raf = null;
	let tMax = $derived(traces ? Math.max(...traces.map((d) => d.points.at(-1)?.[0] || 0)) : 0);

	$effect(() => {
		if (!playing) return;
		let last = performance.now();
		const tick = (now) => {
			const dt = (now - last) / 1000;
			last = now;
			tNow = Math.min(tMax, tNow + dt * speed);
			if (tNow >= tMax) { playing = false; return; }
			raf = requestAnimationFrame(tick);
		};
		raf = requestAnimationFrame(tick);
		return () => cancelAnimationFrame(raf);
	});

	function play() {
		if (tNow >= tMax) tNow = 0;
		playing = !playing;
	}

	// geometry
	let geo = $derived.by(() => {
		if (!traces?.length) return null;
		const all = traces.flatMap((d) => d.points);
		const xs = all.map((p) => p[1]), ys = all.map((p) => p[2]);
		const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
		const scale = 420 / Math.max(maxX - minX, maxY - minY);
		return {
			px: (x) => (x - minX) * scale + 24,
			py: (y) => (maxY - y) * scale + 24,
			vw: (maxX - minX) * scale + 48,
			vh: (maxY - minY) * scale + 48,
		};
	});

	let outlinePath = $derived.by(() => {
		if (!geo || !circuit?.outline?.length) return null;
		return circuit.outline.map((p, i) => (i ? 'L' : 'M') + geo.px(p.x).toFixed(1) + ',' + geo.py(p.y).toFixed(1)).join('') + 'Z';
	});

	function posAt(points, time) {
		let lo = 0, hi = points.length - 1;
		if (time <= points[0][0]) return points[0];
		if (time >= points[hi][0]) return points[hi];
		while (hi - lo > 1) {
			const mid = (lo + hi) >> 1;
			if (points[mid][0] <= time) lo = mid; else hi = mid;
		}
		const a = points[lo], b = points[hi];
		const f = (time - a[0]) / Math.max(0.001, b[0] - a[0]);
		return [time, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f, a[3]];
	}

	let dots = $derived.by(() => {
		if (!traces || !geo) return [];
		return traces.map((d) => {
			const [, x, y, spd] = posAt(d.points, tNow);
			return { driver: d.driver, team: d.team, x: geo.px(x), y: geo.py(y), spd, done: tNow >= (d.points.at(-1)?.[0] || 0) };
		});
	});

	// result table at the end: P after lap 1 (+/- vs qualifying if known)
	let finished = $derived(tNow >= tMax && tMax > 0);
	let resultRows = $derived.by(() => {
		if (!traces) return [];
		return traces
			.filter((d) => d.pos_after != null)
			.sort((a, b) => a.pos_after - b.pos_after)
			.map((d) => {
				const q = qualiPos[d.driver];
				return { driver: d.driver, team: d.team, pos: d.pos_after, delta: q != null ? q - d.pos_after : null };
			});
	});

	function tc(team) { return TEAM_COLORS[team] || '#7D8794'; }
</script>

<div class="sa">
	<div class="sa__bar">
		<button class="sa__play" onclick={play}>{playing ? '❚❚' : tNow >= tMax && tMax > 0 ? '↺' : '▶'}</button>
		<input
			type="range" min="0" max={tMax || 1} step="0.1" value={tNow}
			oninput={(e) => { tNow = +e.target.value; }}
			class="sa__range" aria-label={$t('replay.start_time')}
		/>
		<span class="sa__clock">{tNow.toFixed(1)}s</span>
		<div class="sa__speeds">
			{#each [1, 2, 4] as sp}
				<button class:on={speed === sp} onclick={() => speed = sp}>{sp}x</button>
			{/each}
		</div>
	</div>

	{#if traces && geo}
		<div class="sa__stage">
			<svg viewBox="0 0 {geo.vw} {geo.vh}" class="sa__map" role="img" aria-label={$t('replay.start_title')}>
				{#if outlinePath}<path d={outlinePath} fill="none" stroke="#2E3240" stroke-width="10" stroke-linejoin="round" />{/if}
				{#each dots as d (d.driver)}
					<circle cx={d.x} cy={d.y} r="5" fill={tc(d.team)} stroke="#0F1117" stroke-width="1.2" />
					<text x={d.x + 8} y={d.y + 3} font-size="9" fill={tc(d.team)} font-family="var(--font-mono)" font-weight="700">{d.driver}</text>
				{/each}
			</svg>
			{#if finished}
				<div class="sa__result">
					<span class="sa__rt">{$t('replay.start_result')}</span>
					{#each resultRows.slice(0, 10) as r}
						<div class="sa__rr">
							<span class="sa__rp">{r.pos}</span>
							<span class="sa__rd" style="color:{tc(r.team)}">{r.driver}</span>
							{#if r.delta != null && r.delta !== 0}
								<span class="sa__rdelta" class:up={r.delta > 0} class:down={r.delta < 0}>
									{r.delta > 0 ? '▲' : '▼'}{Math.abs(r.delta)}
								</span>
							{:else}
								<span class="sa__rdelta">&middot;</span>
							{/if}
						</div>
					{/each}
					<p class="sa__note">{$t('replay.start_note')}</p>
				</div>
			{/if}
		</div>
	{:else if failed}
		<p class="sa__empty">{$t('compare.no_telemetry')}</p>
	{:else}
		<p class="sa__empty">...</p>
	{/if}
</div>

<style>
	.sa { background: var(--bg2, #1A1D27); padding: 14px 16px; margin-bottom: 1.25rem; }
	.sa__bar { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
	.sa__play { width: 32px; height: 32px; background: var(--ac, #E24B4A); color: #fff; border: none; font-size: 11px; cursor: pointer; flex: 0 0 32px; }
	.sa__range { flex: 1; accent-color: #E24B4A; cursor: pointer; margin: 0; }
	.sa__clock { font-family: var(--fm, monospace); font-size: 12px; color: #9CA3AF; min-width: 52px; text-align: right; font-variant-numeric: tabular-nums; }
	.sa__speeds { display: flex; gap: 2px; }
	.sa__speeds button { font-family: var(--fm, monospace); font-size: 10px; padding: 4px 10px; background: none; border: 1px solid var(--brd, #2E3240); color: var(--tm, #7D8794); cursor: pointer; }
	.sa__speeds button.on { color: #E8E8ED; background: #0F1117; }
	.sa__stage { display: grid; grid-template-columns: 1fr auto; gap: 16px; align-items: start; }
	.sa__map { width: 100%; max-height: 480px; }
	.sa__result { min-width: 170px; padding: 10px 12px; background: #0F1117; border: 1px solid var(--brd, #2E3240); }
	.sa__rt { display: block; font-family: var(--fm, monospace); font-size: 9px; letter-spacing: .1em; text-transform: uppercase; color: var(--tm, #7D8794); margin-bottom: 8px; }
	.sa__rr { display: grid; grid-template-columns: 20px 40px 1fr; gap: 6px; font-family: var(--fm, monospace); font-size: 11px; padding: 2px 0; }
	.sa__rp { color: var(--tm, #7D8794); }
	.sa__rd { font-weight: 700; }
	.sa__rdelta { text-align: right; color: var(--tm, #7D8794); }
	.sa__rdelta.up { color: #22C55E; }
	.sa__rdelta.down { color: #E24B4A; }
	.sa__note { margin: 8px 0 0; font-size: 9.5px; color: var(--tm, #7D8794); font-family: var(--fm, monospace); line-height: 1.5; max-width: 180px; }
	.sa__empty { color: var(--tm, #7D8794); font-family: var(--fm, monospace); font-size: 12px; }
	@media (max-width: 800px) { .sa__stage { grid-template-columns: 1fr; } }
</style>
