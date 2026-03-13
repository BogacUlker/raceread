<!--
	Race-level insights panel.
	Shows annotations with driver:null/lap:null as insight cards above the charts grid.
-->
<script>
	import { locale } from '$lib/i18n/index.js';
	import { t } from '$lib/i18n/index.js';
	import { ANNOTATION_COLORS } from '$lib/constants.js';

	/** @type {{ annotations: Array }} */
	let { annotations = [] } = $props();

	let insights = $derived(
		annotations.filter((a) => a.driver == null && a.lap == null)
	);

	function getText(a) {
		return $locale === 'tr' ? a.text_tr : a.text_en;
	}

	function getLabel(a) {
		const key = `annotations.${a.category}`;
		return $t(key);
	}

	function getChartLabel(a) {
		const map = { pace: 'charts.pace', energy: 'charts.energy_bars', strategy: 'charts.strategy', delta: 'charts.delta_matrix' };
		return $t(map[a.chart_type] || 'common.lap');
	}
</script>

{#if insights.length > 0}
	<div class="insights-panel">
		<div class="insights-panel__header">
			<span class="insights-panel__title">{$t('annotations.race_insights')}</span>
		</div>
		<div class="insights-panel__grid">
			{#each insights as insight}
				{@const color = ANNOTATION_COLORS[insight.category] || '#888'}
				<div class="insight-card" style="border-left-color: {color}">
					<div class="insight-card__meta">
						<span class="insight-card__category" style="color: {color}">{getLabel(insight)}</span>
						<span class="insight-card__chart">{getChartLabel(insight)}</span>
					</div>
					<div class="insight-card__text">{getText(insight)}</div>
				</div>
			{/each}
		</div>
	</div>
{/if}

<style>
	.insights-panel {
		margin-bottom: var(--space-lg);
	}
	.insights-panel__header {
		margin-bottom: var(--space-sm);
	}
	.insights-panel__title {
		font-family: var(--font-mono);
		font-size: 18px;
		font-weight: 600;
		color: var(--text-primary);
		letter-spacing: -0.01em;
	}
	.insights-panel__grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-sm);
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
	.insight-card__chart {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-muted);
	}
	.insight-card__text {
		font-family: var(--font-mono);
		font-size: 13px;
		line-height: 1.55;
		color: var(--text-secondary);
	}

	@media (max-width: 900px) {
		.insights-panel__grid {
			grid-template-columns: 1fr;
		}
	}
</style>
