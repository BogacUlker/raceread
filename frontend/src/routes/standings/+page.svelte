<script>
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS } from '$lib/constants.js';
	import { favoriteDriver } from '$lib/stores/prefs.js';

	let { data } = $props();
	let standings = $derived(data.standings);
	let calendar = $derived(data.calendar || []);
	let drivers = $derived(standings.drivers || []);
	let constructors = $derived(standings.constructors || []);
	let progression = $derived(standings.progression || []);
	let rounds = $derived(standings.rounds_completed || progression.length);

	function tc(team) { return TEAM_COLORS[team] || '#6B7280'; }
	function roundCode(rnd) { return calendar.find(c => c.round === rnd)?.code || 'R' + rnd; }
	let leaderPts = $derived(drivers[0]?.points || 0);
	let maxConsPts = $derived(constructors[0]?.points || 1);

	// Progression chart: top 10 drivers by current points
	const W = 860, H = 380, ML = 40, MR = 76, MT = 16, MB = 34;
	let chartDrivers = $derived(drivers.slice(0, 10));
	let maxPts = $derived(Math.max(10, ...progression.flatMap(p => Object.values(p.points))));
	function x(rnd) { return ML + ((rnd - 1) / Math.max(1, rounds - 1)) * (W - ML - MR); }
	function y(pts) { return MT + (1 - pts / maxPts) * (H - MT - MB); }
	function pathFor(code) {
		return progression
			.map((p, i) => (i === 0 ? 'M' : 'L') + x(p.round).toFixed(1) + ',' + y(p.points[code] ?? 0).toFixed(1))
			.join(' ');
	}
	// second car of a team gets a dashed line so teammates stay distinguishable
	let dashed = $derived.by(() => {
		const seen = new Set(), out = new Set();
		for (const d of chartDrivers) {
			if (seen.has(d.team)) out.add(d.code);
			seen.add(d.team);
		}
		return out;
	});
	let yTicks = $derived([0, 0.25, 0.5, 0.75, 1].map(f => Math.round(maxPts * f)));

	let hovered = $state(null);

	function toggleFav(code) {
		favoriteDriver.set($favoriteDriver === code ? '' : code);
	}
	// favorite gets full emphasis unless another line is hovered
	function lineOpacity(code) {
		if (hovered) return hovered === code ? 0.95 : 0.15;
		if ($favoriteDriver) return $favoriteDriver === code ? 1 : 0.35;
		return 0.9;
	}
	function lineWidth(code) {
		if (hovered === code) return 3;
		if (!hovered && $favoriteDriver === code) return 3;
		return 2;
	}
</script>

<svelte:head>
	<title>{$t('standings.title')} - RaceRead</title>
</svelte:head>

<div class="st">
	<div class="st__head">
		<a href="/" class="st__back">&larr; {$t('nav.home')}</a>
		<h1 class="st__title">2026 {$t('standings.title')}</h1>
		<p class="st__sub">{$t('standings.after_round')} {rounds} / {calendar.length || rounds}</p>
	</div>

	<!-- Championship progression -->
	<section class="st__card st__card--chart">
		<h2 class="st__card-title">{$t('standings.progression')}</h2>
		<div class="st__chart-wrap">
			<svg viewBox="0 0 {W} {H}" class="st__chart" role="img" aria-label={$t('standings.progression')}>
				{#each yTicks as tick}
					<line x1={ML} x2={W - MR} y1={y(tick)} y2={y(tick)} stroke="var(--border)" stroke-width="1" />
					<text x={ML - 8} y={y(tick) + 3} text-anchor="end" class="st__tick">{tick}</text>
				{/each}
				{#each progression as p}
					<text x={x(p.round)} y={H - MB + 18} text-anchor="middle" class="st__tick">{roundCode(p.round)}</text>
				{/each}
				{#each chartDrivers as d (d.code)}
					<path
						d={pathFor(d.code)}
						fill="none"
						stroke={tc(d.team)}
						stroke-width={lineWidth(d.code)}
						stroke-dasharray={dashed.has(d.code) ? '5 4' : 'none'}
						opacity={lineOpacity(d.code)}
					/>
					<text
						x={x(rounds) + 8}
						y={y(d.points) + 4}
						class="st__line-label"
						fill={tc(d.team)}
						opacity={hovered && hovered !== d.code ? 0.2 : 1}
					>{d.code}{$favoriteDriver === d.code ? ' ★' : ''}</text>
				{/each}
			</svg>
		</div>
		<div class="st__legend">
			{#each chartDrivers as d (d.code)}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<span
					class="st__legend-item"
					onmouseenter={() => hovered = d.code}
					onmouseleave={() => hovered = null}
				>
					<i style="background:{tc(d.team)}"></i>{d.code}
				</span>
			{/each}
		</div>
	</section>

	<div class="st__grid">
		<!-- Drivers -->
		<section class="st__card">
			<h2 class="st__card-title">{$t('standings.drivers')}</h2>
			<table class="st__table">
				<thead>
					<tr>
						<th class="st__pos">#</th>
						<th>{$t('standings.driver')}</th>
						<th>{$t('standings.team')}</th>
						<th class="st__num">{$t('standings.wins')}</th>
						<th class="st__num">{$t('standings.gap')}</th>
						<th class="st__num">{$t('standings.points')}</th>
					</tr>
				</thead>
				<tbody>
					{#each drivers as d (d.code)}
						<tr class:st__row--fav={$favoriteDriver === d.code}>
							<td class="st__pos">{d.position}</td>
							<td class="st__driver">
								<span class="st__bar" style="background:{tc(d.team)}"></span>
								<b>{d.code}</b><span class="st__name">{d.name}</span>
								<button
									class="st__star"
									class:on={$favoriteDriver === d.code}
									title={$t('filter.favorite')}
									aria-label={$t('filter.favorite') + ': ' + d.code}
									onclick={() => toggleFav(d.code)}
								>&#9733;</button>
							</td>
							<td class="st__team">{d.team}</td>
							<td class="st__num">{d.wins || '-'}</td>
							<td class="st__num st__gap">{d.position === 1 ? '-' : '-' + (leaderPts - d.points)}</td>
							<td class="st__num st__pts">{d.points}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</section>

		<!-- Constructors -->
		<section class="st__card">
			<h2 class="st__card-title">{$t('standings.constructors')}</h2>
			<div class="st__cons">
				{#each constructors as c (c.name)}
					<div class="st__cons-row">
						<span class="st__pos">{c.position}</span>
						<span class="st__bar" style="background:{tc(c.name)}"></span>
						<span class="st__cons-name">{c.name}</span>
						<div class="st__cons-track">
							<div class="st__cons-fill" style="width:{(c.points / maxConsPts) * 100}%; background:{tc(c.name)}"></div>
						</div>
						<span class="st__num st__pts">{c.points}</span>
					</div>
				{/each}
			</div>
		</section>
	</div>
</div>

<style>
	.st { color: var(--text-primary); }
	.st__head { margin: 0.5rem 0 1.5rem; }
	.st__back { font-family: var(--font-mono); font-size: 11px; color: var(--accent); text-decoration: none; letter-spacing: .08em; text-transform: uppercase; }
	.st__back:hover { text-decoration: none; opacity: .8; }
	.st__title { font-size: 28px; font-weight: 800; text-transform: uppercase; letter-spacing: -.02em; margin-top: .5rem; }
	.st__sub { font-family: var(--font-mono); font-size: 11px; color: var(--accent); letter-spacing: .1em; text-transform: uppercase; margin-top: 2px; }

	.st__card { background: var(--bg-secondary); padding: 1.25rem 1.5rem; margin-bottom: 1rem; border-left: 2px solid transparent; transition: border-color .2s; }
	.st__card:hover { border-left-color: var(--accent); }
	.st__card-title { font-size: 15px; font-weight: 700; text-transform: uppercase; letter-spacing: .03em; margin-bottom: 1rem; padding-bottom: 8px; border-bottom: 1px solid rgba(46,50,64,.4); }

	.st__chart-wrap { overflow-x: auto; }
	.st__chart { width: 100%; min-width: 640px; height: auto; display: block; }
	.st__tick { font-family: var(--font-mono); font-size: 10px; fill: var(--text-muted); }
	.st__line-label { font-family: var(--font-mono); font-size: 10px; font-weight: 700; }
	.st__legend { display: flex; flex-wrap: wrap; gap: 10px 14px; margin-top: 10px; }
	.st__legend-item { display: inline-flex; align-items: center; gap: 5px; font-family: var(--font-mono); font-size: 10px; color: var(--text-secondary); cursor: default; }
	.st__legend-item i { width: 9px; height: 9px; display: inline-block; }

	.st__grid { display: grid; grid-template-columns: 3fr 2fr; gap: 1rem; align-items: start; }

	.st__table { width: 100%; border-collapse: collapse; }
	.st__table th { font-family: var(--font-mono); font-size: 10px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; text-align: left; padding: 4px 8px 8px; border-bottom: 1px solid var(--border); }
	.st__table td { font-size: 13px; padding: 7px 8px; border-bottom: 1px solid rgba(255,255,255,.04); }
	.st__pos { width: 30px; text-align: center; font-family: var(--font-mono); color: var(--text-muted); }
	.st__driver { display: flex; align-items: center; gap: 8px; font-family: var(--font-mono); }
	.st__bar { width: 3px; height: 15px; flex-shrink: 0; display: inline-block; }
	.st__name { color: var(--text-secondary); font-family: var(--font-body, inherit); }
	.st__team { color: var(--text-secondary); font-size: 12px; }
	.st__num { text-align: right; font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
	.st__gap { color: var(--text-muted); font-size: 12px; }
	.st__pts { font-weight: 700; }
	.st__star { background: none; border: none; padding: 0; font-size: 12px; line-height: 1; color: var(--text-muted); opacity: 0; cursor: pointer; transition: opacity .15s, color .15s; }
	tr:hover .st__star, .st__star.on { opacity: 1; }
	.st__star.on { color: #F59E0B; }
	:global(.st__row--fav) td { background: rgba(245,158,11,.05); }

	.st__cons { display: flex; flex-direction: column; gap: 8px; }
	.st__cons-row { display: flex; align-items: center; gap: 8px; }
	.st__cons-name { font-size: 12.5px; min-width: 110px; }
	.st__cons-track { flex: 1; height: 6px; background: rgba(255,255,255,.05); }
	.st__cons-fill { height: 100%; }

	@media (max-width: 900px) {
		.st__grid { grid-template-columns: 1fr; }
		.st__name { display: none; }
	}
</style>
