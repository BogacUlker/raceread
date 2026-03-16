<!--
	Ideal Laps table - theoretical best lap per driver.
	Best S1 + Best S2 + Best S3 across all qualifying sessions (Q1/Q2/Q3).
	Shows delta between ideal and actual best lap time.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS } from '$lib/constants.js';
	import { formatLapTime } from '$lib/utils/format.js';

	/** @type {{ drivers: Array<any> }} */
	let { drivers } = $props();

	let hoveredRow = $state(null);

	const sessions = ['q1', 'q2', 'q3'];

	/**
	 * Find best sector times across all qualifying sessions.
	 * @param {any} d - driver object with sectors_q1, sectors_q2, sectors_q3
	 * @returns {{ bestS1: {val: number, session: string}, bestS2: {val: number, session: string}, bestS3: {val: number, session: string}, idealTotal: number, actualBest: number, delta: number } | null}
	 */
	function getBestSectors(d) {
		const allS1 = [];
		const allS2 = [];
		const allS3 = [];

		for (const s of sessions) {
			const sectors = d[`sectors_${s}`];
			if (sectors?.s1 != null) allS1.push({ val: sectors.s1, session: s.toUpperCase() });
			if (sectors?.s2 != null) allS2.push({ val: sectors.s2, session: s.toUpperCase() });
			if (sectors?.s3 != null) allS3.push({ val: sectors.s3, session: s.toUpperCase() });
		}

		if (!allS1.length || !allS2.length || !allS3.length) return null;

		const bestS1 = allS1.reduce((a, b) => (a.val < b.val ? a : b));
		const bestS2 = allS2.reduce((a, b) => (a.val < b.val ? a : b));
		const bestS3 = allS3.reduce((a, b) => (a.val < b.val ? a : b));
		const idealTotal = bestS1.val + bestS2.val + bestS3.val;
		const actualBest = Math.min(...[d.q1_s, d.q2_s, d.q3_s].filter(Boolean));
		const delta = actualBest - idealTotal;

		return { bestS1, bestS2, bestS3, idealTotal, actualBest, delta };
	}

	let rows = $derived(
		drivers
			.map((d) => {
				const ideal = getBestSectors(d);
				if (!ideal) return null;
				return { ...d, ...ideal };
			})
			.filter(Boolean)
			.sort((a, b) => a.idealTotal - b.idealTotal)
	);

	let maxDelta = $derived(
		rows.length ? Math.max(...rows.map((r) => r.delta), 0.01) : 0.01
	);

	function textOnColor(hex) {
		const r = parseInt(hex.slice(1, 3), 16);
		const g = parseInt(hex.slice(3, 5), 16);
		const b = parseInt(hex.slice(5, 7), 16);
		const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
		return luminance > 0.5 ? '#000' : '#fff';
	}

	function deltaColor(delta) {
		if (delta < 0.05) return '#22C55E';
		if (delta > 0.1) return '#F59E0B';
		return 'var(--text-secondary)';
	}

	function handleRowEnter(driver) {
		hoveredRow = driver;
	}

	function handleRowLeave() {
		hoveredRow = null;
	}
</script>

<div class="chart-card">
	<div class="chart-card__header">
		<span class="chart-card__title">{$t('qualifying.ideal_lap')}</span>
	</div>

	<div class="ideal-table-wrap">
		<table class="quali-table">
			<thead>
				<tr>
					<th class="col-driver">{$t('qualifying.driver')}</th>
					<th class="col-sector">S1</th>
					<th class="col-sector">S2</th>
					<th class="col-sector">S3</th>
					<th class="col-time">{$t('qualifying.ideal_time')}</th>
					<th class="col-time">{$t('qualifying.actual_best')}</th>
					<th class="col-delta">{$t('qualifying.potential_gain')}</th>
				</tr>
			</thead>
			<tbody>
				{#each rows as row}
					{@const color = TEAM_COLORS[row.team] || '#888'}
					{@const isDimmed = hoveredRow != null && hoveredRow !== row.driver}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<tr
						class:row--dimmed={isDimmed}
						onmouseenter={() => handleRowEnter(row.driver)}
						onmouseleave={handleRowLeave}
					>
						<td class="col-driver">
							<span class="driver-badge" style="background: {color}; color: {textOnColor(color)}">{row.driver}</span>
						</td>
						<td class="col-sector">
							<span class="sector-val">{row.bestS1.val.toFixed(3)}</span>
							<span class="session-label">{row.bestS1.session}</span>
						</td>
						<td class="col-sector">
							<span class="sector-val">{row.bestS2.val.toFixed(3)}</span>
							<span class="session-label">{row.bestS2.session}</span>
						</td>
						<td class="col-sector">
							<span class="sector-val">{row.bestS3.val.toFixed(3)}</span>
							<span class="session-label">{row.bestS3.session}</span>
						</td>
						<td class="col-time ideal-time">{formatLapTime(row.idealTotal)}</td>
						<td class="col-time">{formatLapTime(row.actualBest)}</td>
						<td class="col-delta">
							<div class="delta-cell">
								<span class="delta-text" style="color: {deltaColor(row.delta)}">
									+{row.delta.toFixed(3)}s
								</span>
								<div class="delta-bar-track">
									<div
										class="delta-bar-fill"
										style="width: {(row.delta / maxDelta) * 100}%; background: {deltaColor(row.delta)}"
									></div>
								</div>
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>

<style>
	.ideal-table-wrap {
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

	.col-sector {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.sector-val {
		color: var(--text-primary);
	}
	.session-label {
		display: inline-block;
		font-size: 9px;
		font-weight: 600;
		color: var(--text-muted);
		margin-left: 4px;
		padding: 0 3px;
		background: rgba(255, 255, 255, 0.06);
		border-radius: 2px;
		vertical-align: baseline;
	}

	.col-time {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.ideal-time {
		font-weight: 600;
		color: var(--text-primary);
	}

	.col-delta {
		text-align: right;
		min-width: 120px;
	}
	.delta-cell {
		display: flex;
		align-items: center;
		gap: 8px;
		justify-content: flex-end;
	}
	.delta-text {
		font-variant-numeric: tabular-nums;
		font-size: 11px;
		font-weight: 600;
		flex-shrink: 0;
	}
	.delta-bar-track {
		width: 48px;
		height: 6px;
		background: rgba(255, 255, 255, 0.06);
		border-radius: 3px;
		overflow: hidden;
		flex-shrink: 0;
	}
	.delta-bar-fill {
		height: 100%;
		border-radius: 3px;
		transition: width 0.3s ease;
		opacity: 0.8;
	}

	:global(.row--dimmed) td {
		opacity: 0.3;
	}
	tr {
		transition: opacity 0.15s;
	}
	tr:hover .delta-bar-fill {
		opacity: 1;
	}
</style>
