<!--
	Thin weather strip under the pace chart: track temp (amber area),
	air temp (blue line), wind badge, on the same lap axis.
	Lap mapping is anchored on the chequered flag (+/- 1 lap accuracy).
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { api } from '$lib/api.js';

	let { raceId, totalLaps = 0 } = $props();

	let samples = $state([]);
	$effect(() => {
		if (!raceId) return;
		samples = [];
		api(`/api/races/${raceId}/weather`)
			.then((d) => { samples = d.samples || []; })
			.catch(() => {});
	});

	let width = $state(900);
	const H = 74, PAD = { l: 46, r: 16, t: 8, b: 4 };

	let model = $derived.by(() => {
		const s = samples.filter((x) => x.track_temp != null && x.lap != null);
		if (s.length < 5) return null;
		const temps = s.flatMap((x) => [x.track_temp, x.air_temp]).filter((v) => v != null);
		const lo = Math.floor(Math.min(...temps)) - 1;
		const hi = Math.ceil(Math.max(...temps)) + 1;
		const wind = s.map((x) => x.wind_speed).filter((v) => v != null);
		const rain = s.some((x) => x.rainfall);
		return {
			s, lo, hi, rain,
			windMax: wind.length ? Math.max(...wind) : null,
			trackNow: s[s.length - 1].track_temp,
			trackRange: [Math.min(...s.map((x) => x.track_temp)), Math.max(...s.map((x) => x.track_temp))],
		};
	});

	let x = $derived((lap) => PAD.l + (lap - 1) / Math.max(1, totalLaps - 1) * (width - PAD.l - PAD.r));
	let y = $derived((v) => PAD.t + (1 - (v - model.lo) / (model.hi - model.lo)) * (H - PAD.t - PAD.b));
</script>

{#if model}
	<div class="wst" bind:clientWidth={width}>
		<div class="wst__head">
			<span class="wst__title">{$t('insights.weather')}</span>
			<div class="wst__meta">
				<span><i class="wst__dot wst__dot--track"></i>{$t('insights.track_temp')} {model.trackRange[0].toFixed(0)}-{model.trackRange[1].toFixed(0)}&deg;C</span>
				<span><i class="wst__dot wst__dot--air"></i>{$t('insights.air_temp')}</span>
				{#if model.windMax != null}<span>{$t('insights.wind')} {model.windMax.toFixed(1)} m/s</span>{/if}
				{#if model.rain}<span class="wst__rain">{$t('insights.rain')}</span>{/if}
			</div>
		</div>
		<svg viewBox="0 0 {width} {H}" width={width} height={H} role="img" aria-label={$t('insights.weather')}>
			<polygon
				points="{model.s.map((p) => `${x(p.lap)},${y(p.track_temp)}`).join(' ')} {x(model.s[model.s.length - 1].lap)},{H - PAD.b} {x(model.s[0].lap)},{H - PAD.b}"
				fill="rgba(245,158,11,.12)"
			/>
			<polyline points={model.s.map((p) => `${x(p.lap)},${y(p.track_temp)}`).join(' ')} fill="none" stroke="#F59E0B" stroke-width="1.6" />
			<polyline points={model.s.filter((p) => p.air_temp != null).map((p) => `${x(p.lap)},${y(p.air_temp)}`).join(' ')} fill="none" stroke="#3B82F6" stroke-width="1.3" />
			<text x={PAD.l - 8} y={y(model.hi - 1)} fill="var(--text-muted)" font-size="9" text-anchor="end" dominant-baseline="middle" font-family="var(--font-mono)">{model.hi - 1}&deg;</text>
			<text x={PAD.l - 8} y={y(model.lo + 1)} fill="var(--text-muted)" font-size="9" text-anchor="end" dominant-baseline="middle" font-family="var(--font-mono)">{model.lo + 1}&deg;</text>
		</svg>
	</div>
{/if}

<style>
	.wst { margin-top: 10px; padding: 10px 14px 6px; background: var(--bg-secondary); border: 1px solid var(--border); }
	.wst__head { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 6px; margin-bottom: 4px; }
	.wst__title { font-family: var(--font-mono); font-size: 10px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: var(--text-secondary); }
	.wst__meta { display: flex; gap: 14px; font-family: var(--font-mono); font-size: 9.5px; color: var(--text-muted); flex-wrap: wrap; }
	.wst__meta span { display: inline-flex; align-items: center; gap: 4px; }
	.wst__dot { width: 8px; height: 3px; display: inline-block; }
	.wst__dot--track { background: #F59E0B; }
	.wst__dot--air { background: #3B82F6; }
	.wst__rain { color: #3B82F6; font-weight: 700; }
</style>
