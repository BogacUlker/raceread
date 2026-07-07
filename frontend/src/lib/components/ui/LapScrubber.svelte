<!--
	Lap picker as a mini race timeline: SC/VSC windows shade the track,
	pit stops are dots - you pick a lap SEEING where the story is.
	A real <input type=range> underneath keeps keyboard + SR support.
-->
<script>
	import { t, locale } from '$lib/i18n/index.js';

	let { totalLaps = 58, value = 1, vscLaps = [], scLaps = [], pitLaps = [], onchange = () => {} } = $props();
	let width = $state(300);
	const H = 26;
	let x = $derived((L) => ((L - 1) / Math.max(1, totalLaps - 1)) * width);
</script>

<div class="lsc">
	<span class="lsc__val"><b>{$locale === 'tr' ? 'TUR' : 'LAP'}</b><span>{value}</span></span>
	<div class="lsc__track" bind:clientWidth={width}>
		<svg viewBox="0 0 {width} {H}" width="100%" height={H} preserveAspectRatio="none" aria-hidden="true">
			<rect x="0" y="10" width={width} height="6" fill="rgba(255,255,255,.1)" />
			{#each vscLaps as L}<rect x={x(L) - 2} y="8" width="5" height="10" fill="var(--timing-caution)" opacity=".55" />{/each}
			{#each scLaps as L}<rect x={x(L) - 2} y="8" width="5" height="10" fill="var(--accent)" opacity=".7" />{/each}
			{#each pitLaps as L}<circle cx={x(L)} cy="4" r="2" fill="var(--text-muted)" />{/each}
			<rect x="0" y="10" width={x(value)} height="6" fill="var(--accent)" opacity=".85" />
			<rect x={x(value) - 1.5} y="4" width="4" height="18" fill="#fff" />
		</svg>
		<input
			type="range" min="1" max={totalLaps} value={value}
			oninput={(e) => onchange(+e.target.value)}
			aria-label={$t('tooltip.lap')}
		/>
	</div>
</div>

<style>
	.lsc { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 220px; }
	.lsc__val { display: inline-flex; align-items: stretch; flex-shrink: 0; }
	.lsc__val b { background: var(--accent); color: #fff; font-family: var(--font-heading); font-weight: 900; font-style: italic; font-size: 9.5px; padding: 3px 7px; display: flex; align-items: center; letter-spacing: .05em; }
	.lsc__val span { background: rgba(0,0,0,.6); color: #fff; font-weight: 800; font-size: 12px; padding: 2px 8px; min-width: 26px; text-align: center; font-variant-numeric: tabular-nums; }
	.lsc__track { position: relative; flex: 1; height: 26px; }
	.lsc__track svg { display: block; }
	.lsc__track input {
		position: absolute; inset: 0; width: 100%; height: 100%;
		opacity: 0; cursor: pointer; margin: 0;
	}
	.lsc__track input:focus-visible + svg,
	.lsc__track:focus-within { outline: 1px solid var(--accent-text); outline-offset: 2px; }
</style>
