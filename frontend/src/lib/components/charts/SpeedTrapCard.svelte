<!--
	Speed trap leaderboard - best top speed per driver at the main trap,
	with the other three measurement points as a footer strip.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS } from '$lib/constants.js';
	import { speedTraps } from '$lib/analysis.js';

	let { laps = [] } = $props();
	let traps = $derived(speedTraps(laps));
	let top = $derived((traps.speed_st || []).slice(0, 5));
	let others = $derived([
		{ key: 'I1', e: traps.speed_i1?.[0] },
		{ key: 'I2', e: traps.speed_i2?.[0] },
		{ key: 'FL', e: traps.speed_fl?.[0] },
	].filter((x) => x.e));

	function tc(team) { return TEAM_COLORS[team] || 'var(--text-muted)'; }
</script>

<div class="stc">
	<div class="stc__head">
		<span class="stc__title">{$t('insights.speed_trap')}</span>
		<span class="stc__unit">km/s</span>
	</div>
	{#if top.length}
		{@const max = top[0].v}
		<div class="stc__rows">
			{#each top as e, i}
				<div class="stc__row">
					<span class="stc__rank">{i + 1}</span>
					<span class="stc__drv" style="color:{tc(e.team)}">{e.driver}</span>
					<div class="stc__barwrap"><div class="stc__bar" style="width:{(e.v / max) * 100}%; background:{tc(e.team)}"></div></div>
					<span class="stc__v">{Math.round(e.v)}</span>
					<span class="stc__lap">L{e.lap}</span>
				</div>
			{/each}
		</div>
		<div class="stc__foot">
			{#each others as o}
				<span class="stc__mini"><b>{o.key}</b> {Math.round(o.e.v)} <em style="color:{tc(o.e.team)}">{o.e.driver}</em></span>
			{/each}
		</div>
	{:else}
		<p class="stc__empty">-</p>
	{/if}
</div>

<style>
	.stc { background: var(--bg-secondary); border: 1px solid var(--border); padding: 16px 18px; height: 100%; box-sizing: border-box; }
	.stc__head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px; }
	.stc__title { font-family: var(--font-heading); font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }
	.stc__unit { font-family: var(--font-mono); font-size: 9px; color: var(--text-muted); letter-spacing: .08em; }
	.stc__rows { display: flex; flex-direction: column; gap: 7px; }
	.stc__row { display: grid; grid-template-columns: 14px 34px 1fr 38px 30px; align-items: center; gap: 8px; font-family: var(--font-mono); font-size: 11px; }
	.stc__rank { color: var(--text-muted); font-size: 9px; }
	.stc__drv { font-weight: 600; }
	.stc__barwrap { height: 5px; background: rgba(46,50,64,.6); }
	.stc__bar { height: 100%; }
	.stc__v { text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; }
	.stc__lap { color: var(--text-muted); font-size: 9px; text-align: right; }
	.stc__foot { display: flex; gap: 14px; margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border); font-family: var(--font-mono); font-size: 9.5px; color: var(--text-muted); flex-wrap: wrap; }
	.stc__mini b { color: var(--text-secondary); font-weight: 500; }
	.stc__mini em { font-style: normal; font-weight: 600; }
	.stc__empty { color: var(--text-muted); font-family: var(--font-mono); }
</style>
