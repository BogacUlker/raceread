<!--
	Mini-sector dominance map + corner-by-corner braking analysis.
	One telemetry fetch (both drivers, selected lap) feeds both views:
	- the track line is split into ~30 segments, each painted in the color
	  of whichever driver carries more speed through it
	- per numbered corner: braking point (m before apex) and apex speed
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { api } from '$lib/api.js';

	let { raceId, driver1, driver2, color1, color2, selectedLap = 1, circuit = null } = $props();

	let telemetry = $state(null);
	let loading = $state(false);
	$effect(() => {
		const d1 = driver1, d2 = driver2, lap = selectedLap, id = raceId;
		if (!d1 || !d2 || !id) { telemetry = null; return; }
		loading = true;
		api(`/api/races/${id}/telemetry/compare?d1=${d1}&d2=${d2}&lap=${lap}`)
			.then((r) => { if (d1 === driver1 && d2 === driver2 && lap === selectedLap) { telemetry = r; loading = false; } })
			.catch(() => { telemetry = null; loading = false; });
	});

	const SEGMENTS = 30;

	let model = $derived.by(() => {
		if (!telemetry?.[driver1] || !telemetry?.[driver2]) return null;
		const s1 = telemetry[driver1].samples || [];
		const s2 = telemetry[driver2].samples || [];
		if (s1.length < 30 || s2.length < 30) return null;
		const trackLen = circuit?.track_length || Math.max(...s1.map((s) => s.dist));
		const segLen = trackLen / SEGMENTS;
		const seg = (arr) => {
			const speeds = Array.from({ length: SEGMENTS }, () => []);
			for (const s of arr) {
				const i = Math.min(SEGMENTS - 1, Math.floor((s.dist || 0) / segLen));
				if (s.speed != null) speeds[i].push(s.speed);
			}
			return speeds.map((v) => (v.length ? v.reduce((a, b) => a + b, 0) / v.length : null));
		};
		const v1 = seg(s1), v2 = seg(s2);
		const winners = v1.map((a, i) => {
			const b = v2[i];
			if (a == null || b == null) return 0;
			if (Math.abs(a - b) < 1) return 0;
			return a > b ? 1 : 2;
		});
		const counts = { 1: winners.filter((w) => w === 1).length, 2: winners.filter((w) => w === 2).length, 0: winners.filter((w) => w === 0).length };

		// geometry from d1's racing line
		const xs = s1.map((s) => s.x), ys = s1.map((s) => s.y);
		const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
		const scale = 380 / Math.max(maxX - minX, maxY - minY);
		const px = (x) => (x - minX) * scale + 20;
		const py = (y) => 400 - ((y - minY) * scale + 20) - (400 - (maxY - minY) * scale - 40) / 2;
		const paths = [];
		for (let i = 0; i < SEGMENTS; i++) {
			const pts = s1.filter((s) => Math.floor((s.dist || 0) / segLen) === i);
			if (pts.length < 2) continue;
			paths.push({ w: winners[i], d: pts.map((s, j) => (j ? 'L' : 'M') + px(s.x).toFixed(1) + ',' + py(s.y).toFixed(1)).join('') });
		}
		const vw = (maxX - minX) * scale + 40;

		// corner analysis
		const corners = [];
		for (const c of circuit?.corners || []) {
			const cd = c.distance;
			const windowOf = (arr) => arr.filter((s) => s.dist >= cd - 300 && s.dist <= cd + 60);
			const brakePoint = (arr) => {
				const w = windowOf(arr).sort((a, b) => a.dist - b.dist);
				const first = w.find((s) => s.brake);
				return first ? cd - first.dist : null;
			};
			const apex = (arr) => {
				const w = arr.filter((s) => s.dist >= cd - 80 && s.dist <= cd + 80);
				return w.length ? Math.min(...w.map((s) => s.speed).filter((v) => v != null)) : null;
			};
			const b1 = brakePoint(s1), b2 = brakePoint(s2);
			const a1 = apex(s1), a2 = apex(s2);
			if (a1 == null || a2 == null) continue;
			corners.push({
				n: c.number, letter: c.letter || '',
				b1, b2, a1: Math.round(a1), a2: Math.round(a2),
				brakeDelta: b1 != null && b2 != null ? Math.round(b1 - b2) : null,
				apexDelta: Math.round(a1 - a2),
			});
		}
		return { paths, counts, vw, corners };
	});
</script>

{#if driver1 && driver2}
	<div class="cdm">
		<div class="cdm__head">
			<h2 class="cdm__title">{$t('compare.dominance')} &middot; {$t('tooltip.lap')} {selectedLap}</h2>
			{#if model}
				<div class="cdm__legend">
					<span style="color:{color1}">{driver1} {model.counts[1]}</span>
					<span style="color:{color2}">{driver2} {model.counts[2]}</span>
					{#if model.counts[0]}<span class="cdm__even">{$t('compare.even')} {model.counts[0]}</span>{/if}
				</div>
			{/if}
		</div>
		{#if model}
			<div class="cdm__body">
				<svg viewBox="0 0 {model.vw} 400" class="cdm__map" role="img" aria-label={$t('compare.dominance')}>
					{#each model.paths as p}
						<path d={p.d} fill="none" stroke={p.w === 1 ? color1 : p.w === 2 ? color2 : '#4A4F5E'} stroke-width="7" stroke-linecap="round" />
					{/each}
				</svg>
				{#if model.corners.length}
					<div class="cdm__corners">
						<div class="cdm__crow cdm__crow--head">
							<span>{$t('compare.corner')}</span>
							<span>{$t('compare.brake_point')}</span>
							<span style="color:{color1}">{driver1}</span>
							<span style="color:{color2}">{driver2}</span>
							<span>&Delta; {$t('compare.apex')}</span>
						</div>
						<div class="cdm__cscroll">
							{#each model.corners as c}
								<div class="cdm__crow">
									<span class="cdm__cn">T{c.n}{c.letter}</span>
									<span class="cdm__cb">
										{#if c.brakeDelta == null}
											<em>{$t('compare.flat_out')}</em>
										{:else if Math.abs(c.brakeDelta) < 5}
											<em>=</em>
										{:else}
											<b style="color:{c.brakeDelta < 0 ? color1 : color2}">{c.brakeDelta < 0 ? driver1 : driver2}</b>
											+{Math.abs(c.brakeDelta)}m
										{/if}
									</span>
									<span class="cdm__ca" class:cdm__best={c.apexDelta > 0} style="color:{color1}">{c.a1}</span>
									<span class="cdm__ca" class:cdm__best={c.apexDelta < 0} style="color:{color2}">{c.a2}</span>
									<span class="cdm__cd">{c.apexDelta > 0 ? '+' : ''}{c.apexDelta}</span>
								</div>
							{/each}
						</div>
						<p class="cdm__note">{$t('compare.brake_note')}</p>
					</div>
				{/if}
			</div>
		{:else if loading}
			<p class="cdm__empty">...</p>
		{:else}
			<p class="cdm__empty">{$t('compare.no_telemetry')}</p>
		{/if}
	</div>
{/if}

<style>
	.cdm { background: var(--bgc, #22252F); border: 1px solid var(--brd, #2E3240); padding: 18px 20px; }
	.cdm__head { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
	.cdm__title { font-family: var(--fh, 'Space Grotesk'), sans-serif; font-size: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: .03em; margin: 0; }
	.cdm__legend { display: flex; gap: 14px; font-family: var(--fm, monospace); font-size: 11px; font-weight: 700; }
	.cdm__even { color: var(--tm, #7D8794); font-weight: 400; }
	.cdm__body { display: grid; grid-template-columns: minmax(280px, 1fr) minmax(300px, 1.1fr); gap: 20px; align-items: start; }
	@media (max-width: 900px) { .cdm__body { grid-template-columns: 1fr; } }
	.cdm__map { width: 100%; max-height: 400px; }
	.cdm__corners { font-family: var(--fm, monospace); }
	.cdm__cscroll { max-height: 330px; overflow-y: auto; }
	.cdm__crow { display: grid; grid-template-columns: 44px 1fr 52px 52px 44px; gap: 8px; align-items: baseline; font-size: 11px; padding: 4px 0; border-bottom: 1px solid rgba(46,50,64,.5); }
	.cdm__crow--head { font-size: 9px; color: var(--tm, #7D8794); text-transform: uppercase; letter-spacing: .06em; border-bottom: 1px solid var(--brd, #2E3240); }
	.cdm__cn { color: var(--tm, #7D8794); }
	.cdm__cb em { font-style: normal; color: var(--tm, #7D8794); }
	.cdm__cb b { font-weight: 700; }
	.cdm__ca { text-align: right; font-variant-numeric: tabular-nums; opacity: .75; }
	.cdm__ca.cdm__best { opacity: 1; font-weight: 700; }
	.cdm__cd { text-align: right; color: var(--tm, #7D8794); font-variant-numeric: tabular-nums; }
	.cdm__note { margin: 8px 0 0; font-size: 10px; color: var(--tm, #7D8794); font-family: inherit; line-height: 1.5; }
	.cdm__empty { color: var(--tm, #7D8794); font-family: var(--fm, monospace); font-size: 12px; }
</style>
