<!--
	Race-level insights panel.
	Grouped by chart_type with pill tabs. Click a category to expand its annotations.
-->
<script>
	import { locale } from '$lib/i18n/index.js';
	import { t } from '$lib/i18n/index.js';
	import { ANNOTATION_COLORS } from '$lib/constants.js';

	/** @type {{ annotations: Array, chartTypes?: string[] }} */
	let { annotations = [], chartTypes = null } = $props();

	let insights = $derived(
		annotations
			.filter((a) => a.driver == null && a.lap == null)
			.filter((a) => chartTypes == null || chartTypes.includes(a.chart_type))
	);

	// Group by chart_type
	const CHART_ORDER = ['pace', 'strategy', 'energy', 'delta', 'speed_trace', 'track_map', 'traffic', 'qualifying'];
	const CHART_ICONS = {
		pace: '\u25B6', strategy: '\u25A0', energy: '\u26A1', delta: '\u25C6',
		speed_trace: '\u2248', track_map: '\u25CB', traffic: '\u25AC', qualifying: '\u25B2'
	};

	let grouped = $derived(
		(() => {
			const map = {};
			for (const a of insights) {
				const key = a.chart_type || 'other';
				if (!map[key]) map[key] = [];
				map[key].push(a);
			}
			return CHART_ORDER.filter(k => map[k]).map(k => ({ type: k, items: map[k] }));
		})()
	);

	let activeTab = $state(null);

	function toggleTab(type) {
		activeTab = activeTab === type ? null : type;
	}

	function getText(a) {
		return $locale === 'tr' ? a.text_tr : a.text_en;
	}

	function getLabel(a) {
		return $t(`annotations.${a.category}`);
	}

	function getChartLabel(type) {
		const map = {
			pace: 'charts.pace', energy: 'charts.energy_bars', strategy: 'charts.strategy',
			delta: 'charts.delta_matrix', traffic: 'charts.traffic', qualifying: 'charts.qualifying',
			speed_trace: 'charts.speed_trace', track_map: 'charts.track_map'
		};
		return $t(map[type] || 'common.lap');
	}
</script>

{#if insights.length > 0}
	<div class="insights-panel">
		<div class="insights-panel__header">
			<span class="insights-panel__title">{$t('annotations.race_insights')}</span>
			<span class="insights-panel__count">{insights.length}</span>
		</div>

		<!-- Category pills -->
		<div class="insights-pills">
			{#each grouped as group}
				{@const isActive = activeTab === group.type}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<div
					class="pill"
					class:active={isActive}
					onclick={() => toggleTab(group.type)}
				>
					<span class="pill__icon">{CHART_ICONS[group.type] || '\u25CF'}</span>
					<span class="pill__label">{getChartLabel(group.type)}</span>
					<span class="pill__count">{group.items.length}</span>
				</div>
			{/each}
		</div>

		<!-- Expanded cards for active tab -->
		{#if activeTab}
			{@const activeGroup = grouped.find(g => g.type === activeTab)}
			{#if activeGroup}
				<div class="insights-cards">
					{#each activeGroup.items as insight, i}
						{@const color = ANNOTATION_COLORS[insight.category] || '#888'}
						<div class="insight-card" style="border-left-color: {color}">
							<div class="insight-card__meta">
								<span class="insight-card__category" style="color: {color}">{getLabel(insight)}</span>
								{#if insight.severity === 'high'}
									<span class="insight-card__severity">HIGH</span>
								{/if}
							</div>
							<div class="insight-card__text">{getText(insight)}</div>
						</div>
					{/each}
				</div>
			{/if}
		{/if}
	</div>
{/if}

<style>
	.insights-panel {
		margin-bottom: var(--space-lg);
	}
	.insights-panel__header {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: var(--space-sm);
	}
	.insights-panel__title {
		font-family: var(--font-mono);
		font-size: 18px;
		font-weight: 600;
		color: var(--text-primary);
		letter-spacing: -0.01em;
	}
	.insights-panel__count {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-muted);
		background: var(--bg-secondary);
		padding: 1px 6px;
		border-radius: 8px;
	}

	/* Pills row */
	.insights-pills {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		margin-bottom: var(--space-sm);
	}
	.pill {
		display: flex;
		align-items: center;
		gap: 5px;
		padding: 5px 10px;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: all 0.15s;
		user-select: none;
	}
	.pill:hover {
		border-color: var(--text-muted);
		background: var(--bg-secondary);
	}
	.pill.active {
		background: var(--bg-secondary);
		border-color: var(--text-secondary);
	}
	.pill__icon {
		font-size: 10px;
		color: var(--text-muted);
		line-height: 1;
	}
	.pill.active .pill__icon {
		color: var(--text-primary);
	}
	.pill__label {
		font-family: var(--font-mono);
		font-size: 12px;
		font-weight: 500;
		color: var(--text-secondary);
		white-space: nowrap;
	}
	.pill.active .pill__label {
		color: var(--text-primary);
	}
	.pill__count {
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--text-muted);
		background: var(--bg-primary);
		padding: 0 4px;
		border-radius: 6px;
		min-width: 16px;
		text-align: center;
	}
	.pill.active .pill__count {
		background: var(--bg-card);
		color: var(--text-secondary);
	}

	/* Cards */
	.insights-cards {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-sm);
		animation: slideDown 0.2s ease;
	}
	@keyframes slideDown {
		from { opacity: 0; transform: translateY(-4px); }
		to { opacity: 1; transform: translateY(0); }
	}
	.insight-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-left: 3px solid;
		border-radius: var(--radius-md);
		padding: 10px 12px;
	}
	.insight-card__meta {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 6px;
	}
	.insight-card__category {
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.insight-card__severity {
		font-family: var(--font-mono);
		font-size: 9px;
		font-weight: 600;
		color: var(--accent);
		background: color-mix(in srgb, var(--accent) 12%, transparent);
		padding: 1px 5px;
		border-radius: 3px;
		letter-spacing: 0.04em;
	}
	.insight-card__text {
		font-family: var(--font-mono);
		font-size: 13px;
		line-height: 1.55;
		color: var(--text-secondary);
	}

	@media (max-width: 900px) {
		.insights-cards {
			grid-template-columns: 1fr;
		}
	}
	@media (max-width: 480px) {
		.pill {
			padding: 6px 8px;
			min-height: 36px;
		}
		.pill__label {
			font-size: 11px;
		}
	}
</style>
