<!--
	Consistency ("metronome") ranking - std dev of clean lap times.
	Lower spread = the driver hits the same lap time over and over.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS } from '$lib/constants.js';
	import { metronomScores } from '$lib/analysis.js';

	let { laps = [], vscLaps = [], scLaps = [] } = $props();
	let rows = $derived(metronomScores(laps, vscLaps, scLaps).slice(0, 5));
	function tc(team) { return TEAM_COLORS[team] || 'var(--text-muted)'; }
</script>

<div class="mnc">
	<div class="mnc__head">
		<span class="mnc__title">{$t('insights.metronom')}</span>
		<span class="mnc__unit">&sigma; s</span>
	</div>
	{#if rows.length}
		{@const worst = rows[rows.length - 1].sd}
		<div class="mnc__rows">
			{#each rows as r, i}
				<div class="mnc__row">
					<span class="mnc__rank">{i + 1}</span>
					<span class="mnc__drv" style="color:{tc(r.team)}">{r.driver}</span>
					<div class="mnc__barwrap"><div class="mnc__bar" style="width:{Math.max(8, (1 - r.sd / (worst * 1.3)) * 100)}%; background:{tc(r.team)}"></div></div>
					<span class="mnc__v">&plusmn;{r.sd.toFixed(3)}</span>
				</div>
			{/each}
		</div>
		<p class="mnc__desc">{$t('insights.metronom_desc')}</p>
	{:else}
		<p class="mnc__desc">-</p>
	{/if}
</div>

<style>
	.mnc { background: var(--bg-secondary); border: 1px solid var(--border); padding: 16px 18px; height: 100%; box-sizing: border-box; }
	.mnc__head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px; }
	.mnc__title { display: inline-block; font-family: var(--font-heading); font-size: 10px; font-weight: 900; font-style: italic; color: #fff; background: var(--accent); text-transform: uppercase; letter-spacing: .07em; padding: 3px 10px; }
	.mnc__unit { font-family: var(--font-mono); font-size: 9.5px; color: var(--text-muted); letter-spacing: .08em; }
	.mnc__rows { display: flex; flex-direction: column; gap: 7px; }
	.mnc__row { display: grid; grid-template-columns: 14px 34px 1fr 56px; align-items: center; gap: 8px; font-family: var(--font-mono); font-size: 11px; }
	.mnc__rank { color: var(--text-muted); font-size: 9.5px; }
	.mnc__drv { font-weight: 600; }
	.mnc__barwrap { height: 5px; background: rgba(46,50,64,.6); }
	.mnc__bar { height: 100%; }
	.mnc__v { text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; }
	.mnc__desc { margin: 12px 0 0; padding-top: 10px; border-top: 1px solid var(--border); font-size: 10.5px; color: var(--text-muted); line-height: 1.5; }
</style>
