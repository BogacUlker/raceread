<!--
	Traffic Analysis - summary bars (% in traffic per driver) and lap heatmap.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { scaleLinear, scaleBand } from 'd3-scale';
	import { TEAM_COLORS } from '$lib/constants.js';

	let { trafficData = null, loading: isLoading = false } = $props();

	let viewMode = $state('summary');

	let drivers = $derived(trafficData?.drivers || []);

	// Summary bar chart dimensions
	const barHeight = 24;
	const barGap = 4;
	const labelWidth = 50;
	const margin = { left: 60, right: 20 };

	let maxPct = $derived(Math.max(1, ...drivers.map(d => d.traffic_pct || 0)));
	let barScale = $derived(scaleLinear().domain([0, maxPct]).range([0, 300]));

	function teamColor(driver) {
		const entry = drivers.find(d => d.driver === driver);
		return TEAM_COLORS[entry?.team] || '#888';
	}
</script>

<div class="chart-card">
	<div class="chart-card__header">
		<h3 class="chart-card__title">{$t('charts.traffic')}</h3>
	</div>

	<!-- View toggle -->
	<div class="traffic__controls">
		<div class="traffic__toggle">
			<button class="traffic__toggle-btn" class:active={viewMode === 'summary'} onclick={() => viewMode = 'summary'}>
				{$t('charts.summary_view')}
			</button>
			<button class="traffic__toggle-btn" class:active={viewMode === 'heatmap'} onclick={() => viewMode = 'heatmap'}>
				{$t('charts.heatmap_view')}
			</button>
		</div>
	</div>

	{#if isLoading}
		<div class="traffic__empty">{$t('common.loading')}</div>
	{:else if !trafficData || drivers.length === 0}
		<div class="traffic__empty">{$t('common.no_data')}</div>
	{:else if viewMode === 'summary'}
		<!-- Summary bars -->
		<div class="traffic__summary">
			{#each drivers as d}
				<div class="traffic__row">
					<span class="traffic__label" style="color:{teamColor(d.driver)}">{d.driver}</span>
					<div class="traffic__bar-container">
						<div
							class="traffic__bar"
							style="width:{barScale(d.traffic_pct)}px; background:{teamColor(d.driver)}"
						></div>
						<span class="traffic__pct">{d.traffic_pct.toFixed(1)}%</span>
					</div>
					{#if d.pace_degradation != null}
						<span class="traffic__degradation" class:positive={d.pace_degradation > 0}>
							{d.pace_degradation > 0 ? '+' : ''}{d.pace_degradation.toFixed(2)}s
						</span>
					{/if}
				</div>
			{/each}

			<!-- Legend -->
			<div class="traffic__legend">
				<span class="traffic__legend-item">
					<span class="traffic__legend-bar"></span>
					{$t('charts.traffic_pct')}
				</span>
				<span class="traffic__legend-item">
					{$t('charts.pace_degradation')}
				</span>
			</div>
		</div>
	{:else}
		<!-- Lap heatmap -->
		<div class="traffic__heatmap">
			{#each drivers as d}
				<div class="traffic__heatmap-row">
					<span class="traffic__label" style="color:{teamColor(d.driver)}">{d.driver}</span>
					<div class="traffic__heatmap-laps">
						{#each d.lap_details || [] as lap}
							<div
								class="traffic__heatmap-cell"
								class:in-traffic={lap.in_traffic}
								title="Lap {lap.lap}: {lap.in_traffic ? 'In traffic' : 'Clean air'}{lap.median_gap != null ? ` (gap: ${lap.median_gap}s)` : ''}"
							></div>
						{/each}
					</div>
				</div>
			{/each}
			<div class="traffic__heatmap-legend">
				<span class="traffic__heatmap-chip traffic__heatmap-chip--clean"></span>
				<span>{$t('charts.clean_air')}</span>
				<span class="traffic__heatmap-chip traffic__heatmap-chip--traffic"></span>
				<span>{$t('charts.in_traffic')}</span>
			</div>
		</div>
	{/if}
</div>

<style>
	.traffic__controls {
		margin-bottom: var(--space-md);
	}
	.traffic__toggle {
		display: flex;
		gap: 2px;
	}
	.traffic__toggle-btn {
		font-family: var(--font-mono);
		font-size: var(--font-size-small);
		padding: 4px 10px;
		border: 1px solid var(--border);
		background: transparent;
		color: var(--text-muted);
		cursor: pointer;
		transition: all 0.15s;
	}
	.traffic__toggle-btn:first-child { border-radius: var(--radius-sm) 0 0 var(--radius-sm); }
	.traffic__toggle-btn:last-child { border-radius: 0 var(--radius-sm) var(--radius-sm) 0; }
	.traffic__toggle-btn.active {
		background: var(--bg-secondary);
		color: var(--text-primary);
		border-color: var(--text-muted);
	}
	.traffic__empty {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 150px;
		font-family: var(--font-mono);
		color: var(--text-muted);
	}
	.traffic__summary {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.traffic__row {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
	}
	.traffic__label {
		font-family: var(--font-mono);
		font-size: var(--font-size-small);
		width: 40px;
		text-align: right;
		font-weight: 600;
	}
	.traffic__bar-container {
		display: flex;
		align-items: center;
		gap: 6px;
		flex: 1;
	}
	.traffic__bar {
		height: 16px;
		border-radius: 2px;
		opacity: 0.7;
		min-width: 2px;
		transition: width 0.3s;
	}
	.traffic__pct {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-secondary);
		min-width: 45px;
	}
	.traffic__degradation {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-muted);
		min-width: 55px;
		text-align: right;
	}
	.traffic__degradation.positive {
		color: var(--accent);
	}
	.traffic__legend {
		display: flex;
		gap: var(--space-lg);
		margin-top: var(--space-sm);
		padding-top: var(--space-sm);
		border-top: 1px solid var(--border);
	}
	.traffic__legend-item {
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--text-muted);
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.traffic__legend-bar {
		display: inline-block;
		width: 16px;
		height: 8px;
		background: var(--text-muted);
		border-radius: 2px;
		opacity: 0.5;
	}
	/* Heatmap */
	.traffic__heatmap {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.traffic__heatmap-row {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
	}
	.traffic__heatmap-laps {
		display: flex;
		gap: 1px;
		flex: 1;
	}
	.traffic__heatmap-cell {
		flex: 1;
		height: 16px;
		background: var(--bg-secondary);
		border-radius: 1px;
		min-width: 3px;
		cursor: default;
		transition: background 0.15s;
	}
	.traffic__heatmap-cell.in-traffic {
		background: var(--accent);
		opacity: 0.7;
	}
	.traffic__heatmap-legend {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-top: var(--space-sm);
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--text-muted);
	}
	.traffic__heatmap-chip {
		display: inline-block;
		width: 12px;
		height: 12px;
		border-radius: 2px;
	}
	.traffic__heatmap-chip--clean {
		background: var(--bg-secondary);
	}
	.traffic__heatmap-chip--traffic {
		background: var(--accent);
		opacity: 0.7;
	}
</style>
