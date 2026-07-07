<!--
	Gear map - the track line painted by which gear the car is in,
	the classic FastF1 visualization, live for any driver / lap.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { api } from '$lib/api.js';
	import { TEAM_COLORS } from '$lib/constants.js';

	let { raceId, drivers = [], totalLaps = 58 } = $props();

	// cool-to-hot ramp, gears 1-8
	const GEAR_COLORS = ['#3B4CC0', '#5977E3', '#7DA0F9', '#A8C4FE', '#DDDDDD', '#F5A886', '#E36A53', '#B40426'];

	let driver = $state('');
	let lap = $state(10);
	$effect(() => { if (!driver && drivers.length) driver = drivers[0].driver; });

	let telemetry = $state(null);
	let loading = $state(false);
	$effect(() => {
		const d = driver, l = lap, id = raceId;
		if (!d || !id || !l) return;
		loading = true;
		api(`/api/races/${id}/telemetry?driver=${d}&lap=${l}`)
			.then((r) => { if (d === driver && l === lap) { telemetry = r; loading = false; } })
			.catch(() => { telemetry = null; loading = false; });
	});

	let model = $derived.by(() => {
		const samples = telemetry?.laps?.[0]?.samples || [];
		const pts = samples.filter((s) => s.x != null && s.gear != null);
		if (pts.length < 30) return null;
		const xs = pts.map((s) => s.x), ys = pts.map((s) => s.y);
		const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
		const scale = 360 / Math.max(maxX - minX, maxY - minY);
		const px = (x) => (x - minX) * scale + 20;
		const py = (y) => ((maxY - y) * scale + 20);
		const vh = (maxY - minY) * scale + 40;
		const vw = (maxX - minX) * scale + 40;
		const segs = [];
		let shifts = 0;
		let topGear = 0;
		for (let i = 1; i < pts.length; i++) {
			const g = pts[i].gear;
			if (g !== pts[i - 1].gear) shifts++;
			topGear = Math.max(topGear, g);
			segs.push({
				x1: px(pts[i - 1].x), y1: py(pts[i - 1].y),
				x2: px(pts[i].x), y2: py(pts[i].y),
				c: GEAR_COLORS[Math.min(8, Math.max(1, g)) - 1],
			});
		}
		return { segs, vw, vh, shifts, topGear };
	});

	function tc(code) { return TEAM_COLORS[drivers.find((d) => d.driver === code)?.team] || 'var(--text-muted)'; }
	let lapOptions = $derived(Array.from({ length: totalLaps }, (_, i) => i + 1));
</script>

<div class="chart-card gmp">
	<div class="chart-card__header gmp__head">
		<h3 class="chart-card__title">{$t('telemetry.gear_map')}</h3>
		<div class="gmp__controls">
			<select bind:value={driver} class="gmp__select" aria-label={$t('filter.select_driver')} style="border-color:{tc(driver)}">
				{#each drivers as d}<option value={d.driver}>{d.driver}</option>{/each}
			</select>
			<select bind:value={lap} class="gmp__select" aria-label={$t('tooltip.lap')}>
				{#each lapOptions as l}<option value={l}>L{l}</option>{/each}
			</select>
		</div>
	</div>
	{#if model}
		<div class="gmp__body">
			<svg viewBox="0 0 {model.vw} {model.vh}" class="gmp__map" role="img" aria-label={$t('telemetry.gear_map')}>
				{#each model.segs as s}
					<line x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2} stroke={s.c} stroke-width="6" stroke-linecap="round" />
				{/each}
			</svg>
			<div class="gmp__side">
				<div class="gmp__legend">
					{#each GEAR_COLORS as c, i}
						<span class="gmp__lg"><i style="background:{c}"></i>{i + 1}</span>
					{/each}
				</div>
				<div class="gmp__stats">
					<div><b>{model.shifts}</b> {$t('telemetry.shifts')}</div>
					<div><b>{model.topGear}</b> {$t('telemetry.top_gear')}</div>
				</div>
			</div>
		</div>
	{:else if loading}
		<p class="gmp__empty">...</p>
	{:else}
		<p class="gmp__empty">{$t('compare.no_telemetry')}</p>
	{/if}
</div>

<style>
	.gmp__head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
	.gmp__controls { display: flex; gap: 8px; }
	.gmp__select {
		background: var(--bg-primary); color: var(--text-primary); border: 1px solid var(--border);
		font-family: var(--font-mono); font-size: 11px; padding: 5px 8px; cursor: pointer;
	}
	.gmp__body { display: grid; grid-template-columns: 1fr 90px; gap: 14px; align-items: start; margin-top: 8px; }
	.gmp__map { width: 100%; max-height: 420px; }
	.gmp__side { display: flex; flex-direction: column; gap: 16px; }
	.gmp__legend { display: flex; flex-direction: column; gap: 4px; }
	.gmp__lg { display: inline-flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 10px; color: var(--text-secondary); }
	.gmp__lg i { width: 14px; height: 6px; display: inline-block; }
	.gmp__stats { font-family: var(--font-mono); font-size: 10px; color: var(--text-muted); display: flex; flex-direction: column; gap: 6px; }
	.gmp__stats b { color: var(--text-primary); font-size: 14px; margin-right: 4px; }
	.gmp__empty { color: var(--text-muted); font-family: var(--font-mono); font-size: 12px; }
	@media (max-width: 640px) { .gmp__body { grid-template-columns: 1fr; } .gmp__legend { flex-direction: row; flex-wrap: wrap; } }
</style>
