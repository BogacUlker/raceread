<!--
	Qualifying Results table - position, driver, team, Q1/Q2/Q3 times, gap to pole.
	Red tint for Q1 eliminated, orange for Q2. Sector tooltip on hover.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS } from '$lib/constants.js';
	import { formatLapTime } from '$lib/utils/format.js';
	import { hoveredDriver } from '$lib/stores/race.js';

	/** @type {{ drivers: Array<any> }} */
	let { drivers } = $props();

	let hoveredRow = $state(null);
	const unsubH = hoveredDriver.subscribe(v => { hoveredRow = v; });
	let sectorTooltip = $state(null);
	let tooltipX = $state(0);
	let tooltipY = $state(0);

	function rowClass(d) {
		if (d.eliminated_in === 'Q1') return 'row--q1';
		if (d.eliminated_in === 'Q2') return 'row--q2';
		return '';
	}

	function handleRowEnter(d, e) {
		hoveredDriver.set(d.driver);
		if (d.sectors && (d.sectors.s1 || d.sectors.s2 || d.sectors.s3)) {
			sectorTooltip = d;
			updateTooltipPos(e);
		}
	}

	function handleRowMove(e) {
		updateTooltipPos(e);
	}

	function handleRowLeave() {
		hoveredDriver.set(null);
		sectorTooltip = null;
	}

	function textOnColor(hex) {
		const r = parseInt(hex.slice(1, 3), 16);
		const g = parseInt(hex.slice(3, 5), 16);
		const b = parseInt(hex.slice(5, 7), 16);
		const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
		return luminance > 0.5 ? '#000' : '#fff';
	}

	function updateTooltipPos(e) {
		const container = e.currentTarget.closest('.quali-table-wrap');
		if (!container) return;
		const rect = container.getBoundingClientRect();
		tooltipX = e.clientX - rect.left;
		tooltipY = e.clientY - rect.top;
	}

	function bestTime(d) {
		return d.q3_s || d.q2_s || d.q1_s;
	}
</script>

<div class="chart-card">
	<div class="chart-card__header">
		<span class="chart-card__title">{$t('qualifying.title')}</span>
	</div>

	<div class="quali-table-wrap">
		<table class="quali-table">
			<thead>
				<tr>
					<th class="col-pos">{$t('qualifying.position')}</th>
					<th class="col-driver">{$t('qualifying.driver')}</th>
					<th class="col-team">{$t('qualifying.team')}</th>
					<th class="col-time">{$t('qualifying.q1')}</th>
					<th class="col-time">{$t('qualifying.q2')}</th>
					<th class="col-time">{$t('qualifying.q3')}</th>
					<th class="col-gap">{$t('qualifying.gap')}</th>
						<th class="col-progress">Q1→Q3</th>
				</tr>
			</thead>
			<tbody>
				{#each drivers as d}
					{@const color = TEAM_COLORS[d.team] || '#888'}
					{@const isHovered = hoveredRow === d.driver}
					{@const isDimmed = hoveredRow != null && hoveredRow !== d.driver}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<tr
						class={rowClass(d)}
						class:row--hovered={isHovered}
						class:row--dimmed={isDimmed}
						onmouseenter={(e) => handleRowEnter(d, e)}
						onmousemove={handleRowMove}
						onmouseleave={handleRowLeave}
					>
						<td class="col-pos">{d.position ?? '-'}</td>
						<td class="col-driver">
							<span class="driver-badge" style="background: {color}; color: {textOnColor(color)}">{d.driver}</span>
						</td>
						<td class="col-team">{d.team}</td>
						<td class="col-time">{d.q1 ?? '-'}</td>
						<td class="col-time" class:dimmed={!d.q2}>{d.q2 ?? '-'}</td>
						<td class="col-time" class:dimmed={!d.q3}>{d.q3 ?? '-'}</td>
						<td class="col-gap">
							{#if d.gap_to_pole === 0 || d.gap_to_pole === null}
								{#if d.position === 1}
									<span class="pole-label">{$t('qualifying.pole')}</span>
								{:else}
									-
								{/if}
							{:else}
								+{d.gap_to_pole.toFixed(3)}s
							{/if}
						</td>
						<td class="col-progress">
							{#if d.q1_s && d.q3_s}
								{@const improvement = d.q1_s - d.q3_s}
								<span class="progress-val" class:progress-good={improvement > 0}>
									{improvement > 0 ? '-' : '+'}{Math.abs(improvement).toFixed(2)}s
								</span>
							{:else if d.q1_s && d.q2_s && !d.q3_s}
								{@const improvement = d.q1_s - d.q2_s}
								<span class="progress-val progress-partial" class:progress-good={improvement > 0}>
									{improvement > 0 ? '-' : '+'}{Math.abs(improvement).toFixed(2)}s
								</span>
							{:else}
								<span class="dimmed">-</span>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>

		<!-- Sector tooltip -->
		{#if sectorTooltip}
			<div
				class="sector-tooltip"
				style="left: {tooltipX + 14}px; top: {tooltipY - 50}px;"
			>
				<div class="sector-tooltip__header">{sectorTooltip.driver} - {$t('qualifying.sectors')}</div>
				<div class="sector-tooltip__row">S1: {formatLapTime(sectorTooltip.sectors.s1)}</div>
				<div class="sector-tooltip__row">S2: {formatLapTime(sectorTooltip.sectors.s2)}</div>
				<div class="sector-tooltip__row">S3: {formatLapTime(sectorTooltip.sectors.s3)}</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.quali-table-wrap {
		overflow-x: auto;
		position: relative;
	}
	.quali-table {
		width: 100%;
		border-collapse: collapse;
	}
	.quali-table th,
	.quali-table td {
		font-family: var(--font-mono);
		font-size: 12px;
		padding: 6px 10px;
		white-space: nowrap;
		text-align: left;
	}
	.quali-table th {
		font-size: 11px;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding-bottom: 8px;
		border-bottom: 1px solid var(--border);
	}
	.quali-table td {
		border-bottom: 1px solid rgba(255, 255, 255, 0.04);
	}
	.col-pos {
		width: 40px;
		text-align: center;
	}
	.col-driver {
		font-weight: 600;
	}
	.driver-badge {
		display: inline-block;
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 700;
		padding: 1px 6px;
		border-radius: 3px;
	}
	:global(.row--dimmed) td {
		opacity: 0.3;
	}
	.col-team {
		color: var(--text-secondary);
	}
	.col-time {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.col-gap {
		text-align: right;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
	}
	.dimmed {
		opacity: 0.35;
	}
	.col-progress {
		text-align: right;
		width: 70px;
	}
	.progress-val {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-muted);
		font-variant-numeric: tabular-nums;
	}
	.progress-good {
		color: #22C55E;
	}
	.progress-partial {
		opacity: 0.6;
	}
	.pole-label {
		font-size: 10px;
		font-weight: 700;
		color: var(--accent);
		letter-spacing: 0.06em;
	}

	/* Elimination row tints */
	:global(.row--q1) td {
		background: rgba(239, 68, 68, 0.08);
	}
	:global(.row--q2) td {
		background: rgba(245, 158, 11, 0.08);
	}
	:global(.row--hovered) td {
		background: rgba(255, 255, 255, 0.04);
	}

	.sector-tooltip {
		position: absolute;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: 8px 10px;
		pointer-events: none;
		z-index: 20;
		min-width: 120px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
		font-family: var(--font-mono);
		font-size: 12px;
		color: var(--text-secondary);
	}
	.sector-tooltip__header {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 4px;
		padding-bottom: 4px;
		border-bottom: 1px solid var(--border);
	}
	.sector-tooltip__row {
		padding: 1px 0;
	}
</style>
