<!--
	Sector Comparison - horizontal grouped bars (S1/S2/S3 per driver).
	Fastest sector green, slowest red. Q1/Q2/Q3 filter pills.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS } from '$lib/constants.js';
	import { formatLapTime } from '$lib/utils/format.js';

	/** @type {{ drivers: Array<any> }} */
	let { drivers } = $props();

	let selectedSession = $state('Q3');
	const sessions = ['Q1', 'Q2', 'Q3'];

	// Filter drivers who have a time in the selected session
	let filteredDrivers = $derived(
		drivers.filter((d) => {
			const key = selectedSession.toLowerCase() + '_s';
			return d[key] != null;
		})
	);

	// Get sector times for each driver based on their best lap in selected session
	// We use the sectors stored on each driver entry
	let driverSectors = $derived(
		filteredDrivers.map((d) => ({
			driver: d.driver,
			team: d.team,
			s1: d.sectors?.s1 ?? null,
			s2: d.sectors?.s2 ?? null,
			s3: d.sectors?.s3 ?? null,
		}))
	);

	// Find fastest and slowest for each sector
	let sectorStats = $derived((() => {
		const stats = { s1: { min: Infinity, max: 0 }, s2: { min: Infinity, max: 0 }, s3: { min: Infinity, max: 0 } };
		for (const d of driverSectors) {
			for (const s of ['s1', 's2', 's3']) {
				if (d[s] != null) {
					if (d[s] < stats[s].min) stats[s].min = d[s];
					if (d[s] > stats[s].max) stats[s].max = d[s];
				}
			}
		}
		return stats;
	})());

	// Max total time for bar scaling
	let maxTotal = $derived(
		Math.max(...driverSectors.map((d) => (d.s1 || 0) + (d.s2 || 0) + (d.s3 || 0)), 1)
	);

	function sectorColor(sector, value) {
		if (value == null) return 'var(--text-muted)';
		const stats = sectorStats[sector];
		if (value === stats.min) return '#22C55E';
		if (value === stats.max && driverSectors.length > 2) return '#EF4444';
		return 'var(--text-secondary)';
	}

	function barWidth(value) {
		if (value == null || maxTotal === 0) return 0;
		return (value / maxTotal) * 100;
	}

	let hovered = $state(null);
	let tooltipData = $state(null);
	let tooltipX = $state(0);
	let tooltipY = $state(0);

	function handleEnter(d, e) {
		hovered = d.driver;
		tooltipData = d;
		updatePos(e);
	}

	function handleMove(e) {
		updatePos(e);
	}

	function handleLeave() {
		hovered = null;
		tooltipData = null;
	}

	function updatePos(e) {
		const container = e.currentTarget.closest('.sector-chart');
		if (!container) return;
		const rect = container.getBoundingClientRect();
		tooltipX = e.clientX - rect.left;
		tooltipY = e.clientY - rect.top;
	}
</script>

<div class="chart-card">
	<div class="chart-card__header">
		<span class="chart-card__title">{$t('qualifying.sector_comparison')}</span>
		<div class="session-pills">
			{#each sessions as s}
				<button
					class="pill"
					class:pill--active={selectedSession === s}
					onclick={() => selectedSession = s}
				>
					{s}
				</button>
			{/each}
		</div>
	</div>

	<!-- Legend -->
	<div class="legend">
		<span class="legend__item">
			<span class="legend__dot" style="background: #22C55E"></span>
			{$t('qualifying.fastest')}
		</span>
		<span class="legend__item">
			<span class="legend__dot" style="background: #EF4444"></span>
			{$t('qualifying.slowest')}
		</span>
	</div>

	<div class="sector-chart">
		{#each driverSectors as d}
			{@const color = TEAM_COLORS[d.team] || '#888'}
			{@const isFaded = hovered && hovered !== d.driver}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				class="sector-row"
				class:sector-row--faded={isFaded}
				onmouseenter={(e) => handleEnter(d, e)}
				onmousemove={handleMove}
				onmouseleave={handleLeave}
			>
				<span class="sector-row__driver" style="color: {color}">{d.driver}</span>
				<div class="sector-row__bars">
					{#if d.s1 != null}
						<div
							class="sector-bar s1"
							style="width: {barWidth(d.s1)}%; background: rgba(239, 68, 68, 0.6)"
						></div>
					{/if}
					{#if d.s2 != null}
						<div
							class="sector-bar s2"
							style="width: {barWidth(d.s2)}%; background: rgba(59, 130, 246, 0.6)"
						></div>
					{/if}
					{#if d.s3 != null}
						<div
							class="sector-bar s3"
							style="width: {barWidth(d.s3)}%; background: rgba(168, 85, 247, 0.6)"
						></div>
					{/if}
				</div>
				<div class="sector-row__times">
					<span style="color: {sectorColor('s1', d.s1)}">{formatLapTime(d.s1)}</span>
					<span style="color: {sectorColor('s2', d.s2)}">{formatLapTime(d.s2)}</span>
					<span style="color: {sectorColor('s3', d.s3)}">{formatLapTime(d.s3)}</span>
				</div>
			</div>
		{/each}

		{#if driverSectors.length === 0}
			<p class="no-data">{$t('qualifying.no_time')}</p>
		{/if}

		<!-- Tooltip -->
		{#if tooltipData}
			<div
				class="sector-tooltip"
				style="left: {tooltipX + 14}px; top: {tooltipY - 60}px;"
			>
				<div class="sector-tooltip__header">{tooltipData.driver}</div>
				<div class="sector-tooltip__row">S1: {formatLapTime(tooltipData.s1)}</div>
				<div class="sector-tooltip__row">S2: {formatLapTime(tooltipData.s2)}</div>
				<div class="sector-tooltip__row">S3: {formatLapTime(tooltipData.s3)}</div>
				{#if tooltipData.s1 && tooltipData.s2 && tooltipData.s3}
					<div class="sector-tooltip__row sector-tooltip__total">
						Total: {formatLapTime(tooltipData.s1 + tooltipData.s2 + tooltipData.s3)}
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	.session-pills {
		display: flex;
		gap: 4px;
	}
	.pill {
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 600;
		padding: 3px 10px;
		border: 1px solid var(--border);
		border-radius: 999px;
		background: transparent;
		color: var(--text-muted);
		cursor: pointer;
		transition: all 0.15s;
	}
	.pill:hover {
		border-color: var(--text-muted);
		color: var(--text-secondary);
	}
	.pill--active {
		background: var(--accent);
		border-color: var(--accent);
		color: #fff;
	}

	.legend {
		display: flex;
		gap: var(--space-md);
		margin-bottom: var(--space-md);
	}
	.legend__item {
		display: flex;
		align-items: center;
		gap: 4px;
		font-family: var(--font-mono);
		font-size: 12px;
		color: var(--text-secondary);
	}
	.legend__dot {
		width: 8px;
		height: 8px;
		border-radius: 2px;
	}

	.sector-chart {
		display: flex;
		flex-direction: column;
		gap: 6px;
		position: relative;
	}
	.sector-row {
		display: flex;
		align-items: center;
		gap: 10px;
		transition: opacity 0.15s;
		padding: 2px 0;
	}
	.sector-row--faded {
		opacity: 0.4;
	}
	.sector-row__driver {
		font-family: var(--font-mono);
		font-size: 13px;
		font-weight: 600;
		width: 36px;
		flex-shrink: 0;
	}
	.sector-row__bars {
		flex: 1;
		height: 18px;
		display: flex;
		border-radius: 3px;
		overflow: hidden;
		background: var(--bg-primary);
	}
	.sector-bar {
		height: 100%;
		transition: width 0.3s ease;
	}
	.sector-row__times {
		display: flex;
		gap: 8px;
		font-family: var(--font-mono);
		font-size: 11px;
		font-variant-numeric: tabular-nums;
		flex-shrink: 0;
		width: 200px;
		justify-content: flex-end;
	}
	.no-data {
		font-family: var(--font-mono);
		font-size: 12px;
		color: var(--text-muted);
		text-align: center;
		padding: var(--space-lg);
	}

	.sector-tooltip {
		position: absolute;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: 8px 10px;
		pointer-events: none;
		z-index: 20;
		min-width: 130px;
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
	.sector-tooltip__total {
		margin-top: 4px;
		padding-top: 4px;
		border-top: 1px solid var(--border);
		font-weight: 600;
		color: var(--text-primary);
	}
</style>
