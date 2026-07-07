<!--
	Sustained battles that never show up as position changes: laps spent
	within a second of the same car, from telemetry gap data.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS } from '$lib/constants.js';

	let { battles = [], teamsMap = {} } = $props();
	let rows = $derived(battles.slice(0, 5));
	function tc(driver) { return TEAM_COLORS[teamsMap[driver]] || '#7D8794'; }
	const ICON = { passed: '✓', pit: '◐', stuck: '✕' };
</script>

<div class="btc">
	<div class="btc__head">
		<span class="btc__title">{$t('insights.battles')}</span>
		<span class="btc__unit">{$t('insights.battles_unit')}</span>
	</div>
	{#if rows.length}
		<div class="btc__rows">
			{#each rows as b}
				<div class="btc__row" title="{$t('insights.battle_' + b.resolution)}">
					<span class="btc__chaser" style="color:{tc(b.driver)}">{b.driver}</span>
					<span class="btc__arrow">&rarr;</span>
					<span class="btc__target" style="color:{tc(b.target)}">{b.target}</span>
					<span class="btc__laps">{b.laps} {$t('insights.battle_laps')}</span>
					<span class="btc__range">{b.from}-{b.to}</span>
					<span class="btc__res btc__res--{b.resolution}">{ICON[b.resolution]}</span>
				</div>
			{/each}
		</div>
		<p class="btc__desc">{$t('insights.battles_desc')}</p>
	{:else}
		<p class="btc__desc">{$t('insights.battles_empty')}</p>
	{/if}
</div>

<style>
	.btc { background: var(--bg-secondary, #1A1D27); border: 1px solid var(--border, #2E3240); padding: 16px 18px; height: 100%; box-sizing: border-box; }
	.btc__head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px; }
	.btc__title { font-family: var(--font-heading); font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }
	.btc__unit { font-family: var(--font-mono); font-size: 9px; color: var(--text-muted, #7D8794); letter-spacing: .08em; }
	.btc__rows { display: flex; flex-direction: column; gap: 7px; }
	.btc__row { display: grid; grid-template-columns: 34px 14px 34px 1fr 44px 16px; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 11px; }
	.btc__chaser, .btc__target { font-weight: 700; }
	.btc__arrow { color: var(--text-muted, #7D8794); }
	.btc__laps { color: var(--text-secondary, #9CA3AF); text-align: right; }
	.btc__range { color: var(--text-muted, #7D8794); font-size: 9.5px; text-align: right; }
	.btc__res { text-align: center; font-size: 10px; }
	.btc__res--passed { color: #22C55E; }
	.btc__res--pit { color: #F59E0B; }
	.btc__res--stuck { color: #E24B4A; }
	.btc__desc { margin: 12px 0 0; padding-top: 10px; border-top: 1px solid var(--border, #2E3240); font-size: 10.5px; color: var(--text-muted, #7D8794); line-height: 1.5; }
</style>
