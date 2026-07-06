<!--
	Energy Duel - two drivers' lap-by-lap deploy/clip bars, mirrored around
	a center line. The "who is pushing vs who is battery-limited" view.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS, ENERGY_COLORS } from '$lib/constants.js';
	import { api } from '$lib/api.js';

	let { raceId, drivers = [], d1init = '', d2init = '', totalLaps = 58 } = $props();

	let d1 = $state('');
	let d2 = $state('');
	let win = $state('all'); // all | first10 | last10
	let cache = new Map();
	let data1 = $state(null);
	let data2 = $state(null);

	$effect(() => {
		if (!d1 && drivers.length >= 2) {
			d1 = d1init && drivers.some((d) => d.driver === d1init) ? d1init : drivers[0].driver;
			d2 = d2init && drivers.some((d) => d.driver === d2init) && d2init !== d1 ? d2init : (drivers.find((d) => d.driver !== d1)?.driver ?? '');
		}
	});

	async function load(code, slot) {
		if (!code) return;
		if (!cache.has(code)) {
			try {
				cache.set(code, await api(`/api/races/${raceId}/energy?driver=${code}`));
			} catch { cache.set(code, null); }
		}
		if (slot === 1) data1 = cache.get(code);
		else data2 = cache.get(code);
	}
	$effect(() => { load(d1, 1); });
	$effect(() => { load(d2, 2); });

	function team(code) { return drivers.find((x) => x.driver === code)?.team || ''; }
	function tc(code) { return TEAM_COLORS[team(code)] || '#888'; }

	function windowed(laps) {
		if (!laps) return [];
		if (win === 'first10') return laps.slice(0, 10);
		if (win === 'last10') return laps.slice(-10);
		return laps;
	}

	let laps1 = $derived(windowed(data1?.laps));
	let laps2 = $derived(windowed(data2?.laps));
	let lapNos = $derived(laps1.map((l) => l.lap));
	let maxVal = $derived(Math.max(
		6,
		...laps1.map((l) => (l.normalized_deploy || 0) + (l.normalized_clip || 0)),
		...laps2.map((l) => (l.normalized_deploy || 0) + (l.normalized_clip || 0))
	));

	const W = 640, H = 190, MID = 88, MAXBAR = 70, X0 = 34, XW = W - X0 - 10;
	function bx(i) { return X0 + (i / Math.max(1, lapNos.length - 1)) * XW; }
	let barW = $derived(Math.max(2.5, Math.min(9, (XW / Math.max(1, lapNos.length)) * 0.6)));
	function h(v) { return ((v || 0) / maxVal) * MAXBAR; }
</script>

<div class="chart-card">
	<div class="chart-card__header">
		<span class="chart-card__title">{$t('energy.duel')}</span>
		<div class="duel-ctrl">
			<select bind:value={d1} aria-label="Driver 1">
				{#each drivers as d}<option value={d.driver} disabled={d.driver === d2}>{d.driver}</option>{/each}
			</select>
			<span class="duel-vs">vs</span>
			<select bind:value={d2} aria-label="Driver 2">
				{#each drivers as d}<option value={d.driver} disabled={d.driver === d1}>{d.driver}</option>{/each}
			</select>
			<div class="duel-win">
				<button class:on={win === 'all'} onclick={() => win = 'all'}>{$t('energy.window_all')}</button>
				<button class:on={win === 'first10'} onclick={() => win = 'first10'}>{$t('energy.window_first10')}</button>
				<button class:on={win === 'last10'} onclick={() => win = 'last10'}>{$t('energy.window_last10')}</button>
			</div>
		</div>
	</div>

	{#if laps1.length && laps2.length}
		<svg viewBox="0 0 {W} {H}" class="duel-svg" role="img" aria-label={$t('energy.duel')}>
			<!-- VSC bands -->
			{#each laps1 as l, i}
				{#if l.is_vsc}
					<rect x={bx(i) - barW / 2 - 1} y={MID - MAXBAR} width={barW + 2} height={MAXBAR * 2} fill="#F59E0B" opacity="0.08" />
				{/if}
			{/each}
			<!-- driver 1: up -->
			{#each laps1 as l, i}
				{@const dep = h(l.normalized_deploy)}
				{@const clip = h(l.normalized_clip)}
				{#if dep > 0.4}<rect x={bx(i) - barW / 2} y={MID - dep} width={barW} height={dep} fill={ENERGY_COLORS.deploy} opacity="0.9" />{/if}
				{#if clip > 0.4}<rect x={bx(i) - barW / 2} y={MID - dep - clip} width={barW} height={clip} fill={ENERGY_COLORS.clip} opacity="0.95" />{/if}
			{/each}
			<!-- driver 2: down -->
			{#each laps2 as l, i}
				{@const dep = h(l.normalized_deploy)}
				{@const clip = h(l.normalized_clip)}
				{#if dep > 0.4}<rect x={bx(i) - barW / 2} y={MID + 4} width={barW} height={dep} fill={ENERGY_COLORS.deploy} opacity="0.9" />{/if}
				{#if clip > 0.4}<rect x={bx(i) - barW / 2} y={MID + 4 + dep} width={barW} height={clip} fill={ENERGY_COLORS.clip} opacity="0.95" />{/if}
			{/each}
			<line x1="0" x2={W} y1={MID + 2} y2={MID + 2} stroke="#2E3240" />
			<text x="4" y={MID - MAXBAR + 4} class="duel-code" fill={tc(d1)}>{d1}</text>
			<text x="4" y={MID + MAXBAR + 12} class="duel-code" fill={tc(d2)}>{d2}</text>
			{#each lapNos as lap, i}
				{#if lap % 10 === 0 || lapNos.length <= 12}
					<text x={bx(i)} y={H - 4} text-anchor="middle" class="duel-tick">L{lap}</text>
				{/if}
			{/each}
		</svg>
		<div class="duel-legend">
			<span><i style="background:{ENERGY_COLORS.deploy}"></i>{$t('charts.deploy')}</span>
			<span><i style="background:{ENERGY_COLORS.clip}"></i>{$t('charts.clip')}</span>
			<span><i style="background:#F59E0B;opacity:.25"></i>VSC</span>
		</div>
	{:else}
		<div class="duel-empty">{$t('common.loading')}</div>
	{/if}
</div>

<style>
	.duel-ctrl { margin-left: auto; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
	.duel-ctrl select {
		font-family: var(--font-mono); font-size: 12px; padding: 3px 8px;
		background: var(--bg-primary); color: var(--text-primary);
		border: 1px solid var(--border); cursor: pointer;
	}
	.duel-vs { font-family: var(--font-mono); font-size: 10px; color: var(--text-muted); }
	.duel-win { display: flex; gap: 2px; }
	.duel-win button {
		font-family: var(--font-mono); font-size: 10px; padding: 3px 8px;
		background: none; border: 1px solid var(--border); color: var(--text-muted); cursor: pointer;
	}
	.duel-win button.on { color: var(--text-primary); background: var(--bg-secondary); }
	.duel-svg { width: 100%; height: auto; display: block; }
	.duel-code { font-family: var(--font-mono); font-size: 11px; font-weight: 700; }
	.duel-tick { font-family: var(--font-mono); font-size: 8.5px; fill: var(--text-muted); }
	.duel-legend { display: flex; gap: 14px; margin-top: 6px; font-family: var(--font-mono); font-size: 10px; color: var(--text-secondary); }
	.duel-legend i { display: inline-block; width: 8px; height: 8px; margin-right: 4px; }
	.duel-empty { padding: 3rem; text-align: center; font-family: var(--font-mono); font-size: 12px; color: var(--text-muted); }
</style>
