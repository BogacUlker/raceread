<!--
	Delta Matrix - NxN heatmap table showing driver-to-driver median gap.
	HTML table with diverging color scale.
	Row/column highlight on hover, cross-chart driver highlight.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS } from '$lib/constants.js';
	import { scaleSequential } from 'd3-scale';
	import { interpolateRdYlGn } from 'd3-scale-chromatic';
	import { max } from 'd3-array';
	import { formatDelta } from '$lib/utils/format.js';
	import { hoveredDriver } from '$lib/stores/race.js';

	/**
	 * @type {{
	 *   drivers: string[],
	 *   matrix: number[][],
	 *   teams: Record<string, string>
	 * }}
	 */
	let { drivers, matrix, teams = {} } = $props();

	// Find max absolute delta for symmetric color scale
	let maxDelta = $derived(
		(() => {
			let m = 0;
			for (const row of matrix) {
				for (const val of row) {
					if (val != null && Math.abs(val) > m) m = Math.abs(val);
				}
			}
			return m || 1;
		})()
	);

	// Green = negative (faster), Red = positive (slower)
	let colorScale = $derived(
		scaleSequential(interpolateRdYlGn).domain([maxDelta, -maxDelta])
	);

	// Hover state
	let hoveredCell = $state(null);
	let tooltipX = $state(0);
	let tooltipY = $state(0);

	function handleCellEnter(row, col, e) {
		hoveredCell = { row, col };
		hoveredDriver.set(drivers[row]);
		updateTooltipPos(e);
	}

	function handleCellMove(e) {
		updateTooltipPos(e);
	}

	function handleCellLeave() {
		hoveredCell = null;
		hoveredDriver.set(null);
	}

	function updateTooltipPos(e) {
		const container = e.currentTarget.closest('.matrix-wrap');
		if (!container) return;
		const rect = container.getBoundingClientRect();
		tooltipX = e.clientX - rect.left;
		tooltipY = e.clientY - rect.top;
	}
</script>

<div class="chart-card">
	<div class="chart-card__header">
		<span class="chart-card__title">{$t('charts.delta_matrix')}</span>
	</div>

	<div class="matrix-wrap">
		<table class="matrix">
			<thead>
				<tr>
					<th></th>
					{#each drivers as d, j}
						{@const color = TEAM_COLORS[teams[d]] || '#888'}
						<th
							class="matrix__col-header"
							class:col-highlight={hoveredCell && hoveredCell.col === j}
							style="color: {color}"
						>
							{d}
						</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each drivers as rowDriver, i}
					{@const rowColor = TEAM_COLORS[teams[rowDriver]] || '#888'}
					<tr class:row-highlight={hoveredCell && hoveredCell.row === i}>
						<td
							class="matrix__row-header"
							class:row-highlight={hoveredCell && hoveredCell.row === i}
							style="color: {rowColor}"
						>
							{rowDriver}
						</td>
						{#each matrix[i] as val, j}
							{@const isDiag = i === j}
							{@const isHovered = hoveredCell && hoveredCell.row === i && hoveredCell.col === j}
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<td
								class="matrix__cell"
								class:diagonal={isDiag}
								class:cell-hovered={isHovered}
								class:col-highlight={hoveredCell && hoveredCell.col === j && !isHovered}
								style={!isDiag && val != null
									? `background: ${colorScale(val)}; color: ${Math.abs(val) > maxDelta * 0.6 ? '#000' : '#333'}`
									: ''}
								onmouseenter={(e) => handleCellEnter(i, j, e)}
								onmousemove={handleCellMove}
								onmouseleave={handleCellLeave}
							>
								{isDiag ? '-' : formatDelta(val)}
							</td>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>

		<!-- Floating tooltip -->
		{#if hoveredCell && hoveredCell.row !== hoveredCell.col}
			{@const rowDriver = drivers[hoveredCell.row]}
			{@const colDriver = drivers[hoveredCell.col]}
			{@const val = matrix[hoveredCell.row][hoveredCell.col]}
			<div
				class="delta-tooltip"
				style="left: {tooltipX + 14}px; top: {tooltipY - 36}px;"
			>
				{rowDriver} vs {colDriver}: <strong>{formatDelta(val)}</strong>s
			</div>
		{/if}
	</div>
</div>

<style>
	.matrix-wrap {
		overflow-x: auto;
		position: relative;
	}
	.matrix {
		border-collapse: collapse;
		width: 100%;
	}
	.matrix th,
	.matrix td {
		font-family: var(--font-mono);
		font-size: 11px;
		padding: 6px 8px;
		text-align: center;
		white-space: nowrap;
		transition: background 0.1s;
	}
	.matrix__col-header {
		font-weight: 600;
		font-size: 12px;
		padding-bottom: 8px;
	}
	.matrix__row-header {
		font-weight: 600;
		font-size: 12px;
		text-align: right;
		padding-right: 10px;
	}
	.matrix__cell {
		border-radius: 3px;
		min-width: 52px;
		cursor: default;
	}
	.matrix__cell.diagonal {
		color: var(--text-muted);
		background: transparent;
	}

	/* Row/column highlight on hover */
	.row-highlight {
		background: rgba(255, 255, 255, 0.03);
	}
	.col-highlight {
		background: rgba(255, 255, 255, 0.03);
	}
	.cell-hovered {
		outline: 2px solid var(--text-secondary);
		outline-offset: -1px;
	}

	.delta-tooltip {
		position: absolute;
		font-family: var(--font-mono);
		font-size: 13px;
		color: var(--text-primary);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		padding: 6px 10px;
		border-radius: 4px;
		pointer-events: none;
		z-index: 20;
		white-space: nowrap;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
	}
</style>
