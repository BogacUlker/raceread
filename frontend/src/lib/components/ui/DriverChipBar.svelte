<!--
	Broadcast driver picker - team-striped TLA chips instead of a <select>.
	The whole field is visible at a glance; the favorite driver leads.
	max=1: radio behavior. max=2: first two picks get 1/2 badges (compare).
-->
<script>
	import { favoriteDriver } from '$lib/stores/prefs.js';
	import { TEAM_COLORS } from '$lib/constants.js';

	let { drivers = [], selected = [], max = 1, onchange = () => {} } = $props();

	let ordered = $derived.by(() => {
		const fav = $favoriteDriver;
		if (!fav) return drivers;
		const i = drivers.findIndex((d) => d.driver === fav);
		return i > 0 ? [drivers[i], ...drivers.slice(0, i), ...drivers.slice(i + 1)] : drivers;
	});

	function toggle(code) {
		let next;
		if (selected.includes(code)) next = selected.filter((c) => c !== code);
		else if (max === 1) next = [code];
		else if (selected.length < max) next = [...selected, code];
		else next = [...selected.slice(1), code]; // rotate oldest out
		onchange(next);
	}
	function tc(team) { return TEAM_COLORS[team] || '#848C99'; }
</script>

<div class="dcb" role="group">
	{#each ordered as d (d.driver)}
		{@const idx = selected.indexOf(d.driver)}
		<button
			class="dcb__chip" class:dcb__chip--on={idx >= 0}
			aria-pressed={idx >= 0}
			style="--team: {tc(d.team)}"
			onclick={() => toggle(d.driver)}
		>
			<span class="dcb__bar"></span>
			{d.driver}
			{#if max > 1 && idx >= 0}<b class="dcb__n">{idx + 1}</b>{/if}
			{#if $favoriteDriver === d.driver}<span class="dcb__fav">★</span>{/if}
		</button>
	{/each}
</div>

<style>
	.dcb { display: flex; flex-wrap: wrap; gap: 4px; }
	.dcb__chip {
		display: inline-flex; align-items: center; gap: 6px;
		background: var(--bg-card); border: 1px solid var(--border);
		color: var(--text-secondary);
		font-family: var(--font-heading); font-weight: 800; font-size: 11.5px; letter-spacing: .05em;
		padding: 4px 9px 4px 0; cursor: pointer;
		transition: border-color .12s, color .12s, background .12s;
	}
	.dcb__bar { width: 4px; align-self: stretch; background: var(--team); }
	.dcb__chip:hover { color: var(--text-primary); border-color: var(--team); }
	.dcb__chip--on { color: #fff; border-color: var(--accent); background: rgba(225,6,0,.12); }
	.dcb__n {
		font-family: var(--font-varsity); font-size: 9px; font-weight: 400;
		background: var(--accent); color: #fff; padding: 0 4px; line-height: 1.4;
	}
	.dcb__fav { color: var(--timing-caution); font-size: 9px; }
	@media (max-width: 640px) {
		.dcb { flex-wrap: nowrap; overflow-x: auto; padding-bottom: 4px; }
	}
</style>
