<!--
	Quick navigation pill bar for dashboard sections.
	Click a pill to expand (if collapsed) and scroll to that section.
	Session-aware: shows race or qualifying sections based on activeSession.
-->
<script>
	import { tick } from 'svelte';
	import { t } from '$lib/i18n/index.js';
	import { collapsedSections, SECTIONS, QUALIFYING_SECTIONS } from '$lib/stores/dashboard.js';
	import { activeSession } from '$lib/stores/race.js';

	const LABELS = {
		insights: 'chart_nav.insights',
		pace: 'chart_nav.pace',
		strategy: 'chart_nav.strategy',
		energy: 'chart_nav.energy',
		'energy-timeline': 'chart_nav.energy_timeline',
		'speed-trace': 'chart_nav.speed_trace',
		'track-map': 'chart_nav.track_map',
		'traffic': 'chart_nav.traffic',
		'qualifying-results': 'chart_nav.qualifying_results',
		'sector-comparison': 'chart_nav.sector_comparison',
		'qualifying-delta': 'chart_nav.qualifying_delta'
	};

	let collapsed = $state({});
	const unsub = collapsedSections.subscribe((v) => { collapsed = v; });

	let session = $state('race');
	const unsubSession = activeSession.subscribe((v) => { session = v; });

	let activeSections = $derived(session === 'qualifying' ? QUALIFYING_SECTIONS : SECTIONS);
	let allCollapsed = $derived(activeSections.every((s) => collapsed[s]));

	async function navigateTo(sectionId) {
		if (collapsed[sectionId]) {
			collapsedSections.toggle(sectionId);
			await tick();
		}
		const el = document.getElementById(`section-${sectionId}`);
		if (el) {
			el.scrollIntoView({ behavior: 'smooth', block: 'start' });
		}
	}

	function toggleAll() {
		if (allCollapsed) {
			collapsedSections.expandAll();
		} else {
			collapsedSections.collapseAll();
		}
	}
</script>

<nav class="chart-nav">
	<div class="chart-nav__pills">
		{#each activeSections as sectionId}
			<button
				class="chart-nav__pill"
				class:muted={collapsed[sectionId]}
				onclick={() => navigateTo(sectionId)}
			>
				{$t(LABELS[sectionId])}
			</button>
		{/each}
	</div>
	{#if session === 'race'}
		<button class="chart-nav__toggle" onclick={toggleAll}>
			{allCollapsed ? $t('chart_nav.expand_all') : $t('chart_nav.collapse_all')}
		</button>
	{/if}
</nav>

<style>
	.chart-nav {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		margin-bottom: var(--space-lg);
		flex-wrap: wrap;
	}
	.chart-nav__pills {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
	}
	.chart-nav__pill {
		font-family: var(--font-mono);
		font-size: var(--font-size-label);
		padding: 5px 14px;
		border: 1px solid var(--border);
		border-radius: 999px;
		background: transparent;
		color: var(--text-primary);
		cursor: pointer;
		transition: all 0.15s;
	}
	.chart-nav__pill:hover {
		border-color: var(--text-muted);
		background: var(--bg-secondary);
	}
	.chart-nav__pill.muted {
		opacity: 0.4;
	}
	.chart-nav__toggle {
		font-family: var(--font-mono);
		font-size: var(--font-size-label);
		padding: 5px 14px;
		border: 1px solid var(--border);
		border-radius: 999px;
		background: transparent;
		color: var(--text-muted);
		cursor: pointer;
		margin-left: auto;
		transition: all 0.15s;
	}
	.chart-nav__toggle:hover {
		color: var(--text-secondary);
		border-color: var(--text-muted);
	}
</style>
