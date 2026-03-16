<!--
	Qualifying Driver Detail Page - individual driver qualifying attempts breakdown.
	Shows all Q1/Q2/Q3 laps with sectors, improvement chart, and best sectors summary.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS, COMPOUND_COLORS } from '$lib/constants.js';
	import { formatLapTime } from '$lib/utils/format.js';

	let { data } = $props();

	let raceId = $derived(data.raceId);
	let raceInfo = $derived(data.raceInfo);
	let driverCode = $derived(data.driverCode);

	let driverData = $derived.by(() => {
		const drivers = data.qualifying?.drivers || [];
		return drivers.find((d) => d.driver === driverCode) || null;
	});

	let teamColor = $derived(TEAM_COLORS[driverData?.team] || '#888');

	// All other drivers for animation compare
	let otherDrivers = $derived(
		(data.qualifying?.drivers || [])
			.filter(d => d.driver !== driverCode)
			.sort((a, b) => (a.position ?? 99) - (b.position ?? 99))
	);
	let compareTarget = $state('');

	let attempts = $derived(driverData?.attempts || []);
	let hasAttempts = $derived(attempts.length > 0);

	// Group attempts by session
	let attemptsBySession = $derived.by(() => {
		const groups = { Q1: [], Q2: [], Q3: [] };
		for (const a of attempts) {
			if (groups[a.session]) {
				groups[a.session].push(a);
			}
		}
		return groups;
	});

	// Sessions that have at least one attempt
	let activeSessions = $derived(
		['Q1', 'Q2', 'Q3'].filter((s) => attemptsBySession[s].length > 0)
	);

	// Best sectors across all attempts (non-deleted)
	let bestSectors = $derived.by(() => {
		const valid = attempts.filter((a) => !a.is_deleted && a.time_s != null);
		if (!valid.length) return null;

		let bestS1 = { value: Infinity, attempt: null };
		let bestS2 = { value: Infinity, attempt: null };
		let bestS3 = { value: Infinity, attempt: null };

		for (const a of valid) {
			if (a.s1 != null && a.s1 < bestS1.value) {
				bestS1 = { value: a.s1, attempt: a };
			}
			if (a.s2 != null && a.s2 < bestS2.value) {
				bestS2 = { value: a.s2, attempt: a };
			}
			if (a.s3 != null && a.s3 < bestS3.value) {
				bestS3 = { value: a.s3, attempt: a };
			}
		}

		return {
			s1: bestS1.attempt ? bestS1 : null,
			s2: bestS2.attempt ? bestS2 : null,
			s3: bestS3.attempt ? bestS3 : null,
		};
	});

	// Theoretical best from best sectors
	let theoreticalBest = $derived.by(() => {
		if (!bestSectors || !bestSectors.s1 || !bestSectors.s2 || !bestSectors.s3) return null;
		return bestSectors.s1.value + bestSectors.s2.value + bestSectors.s3.value;
	});

	// Improvement chart data - valid (non-deleted) attempts in chronological order
	let chartAttempts = $derived(
		attempts.filter((a) => !a.is_deleted && a.time_s != null)
	);

	// SVG chart dimensions
	const chartW = 1000;
	const chartH = 300;
	const margin = { top: 28, right: 28, bottom: 44, left: 68 };
	const yTicks = 5;
	const innerW = chartW - margin.left - margin.right;
	const innerH = chartH - margin.top - margin.bottom;

	// Chart scales
	let timeRange = $derived.by(() => {
		if (chartAttempts.length === 0) return { min: 0, max: 1 };
		const times = chartAttempts.map((a) => a.time_s);
		const min = Math.min(...times);
		const max = Math.max(...times);
		const pad = (max - min) * 0.15 || 0.5;
		return { min: min - pad, max: max + pad };
	});

	function xScale(index) {
		if (chartAttempts.length <= 1) return margin.left + innerW / 2;
		return margin.left + (index / (chartAttempts.length - 1)) * innerW;
	}

	function yScale(time) {
		const { min, max } = timeRange;
		if (max === min) return margin.top + innerH / 2;
		return margin.top + ((time - min) / (max - min)) * innerH;
	}

	// Session separator positions for the chart
	let sessionSeparators = $derived.by(() => {
		const seps = [];
		let prevSession = null;
		for (let i = 0; i < chartAttempts.length; i++) {
			if (prevSession && chartAttempts[i].session !== prevSession) {
				// Place separator between previous and current point
				seps.push({
					x: (xScale(i - 1) + xScale(i)) / 2,
					label: chartAttempts[i].session,
				});
			}
			prevSession = chartAttempts[i].session;
		}
		return seps;
	});

	// Line path for the improvement chart
	let linePath = $derived.by(() => {
		if (chartAttempts.length === 0) return '';
		return chartAttempts
			.map((a, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i).toFixed(1)} ${yScale(a.time_s).toFixed(1)}`)
			.join(' ');
	});

	// Smart label placement: above for fast laps (local max on chart), below for slow laps (local min on chart)
	function labelYOffset(index) {
		const curr = chartAttempts[index].time_s;
		const prev = index > 0 ? chartAttempts[index - 1].time_s : null;
		const next = index < chartAttempts.length - 1 ? chartAttempts[index + 1].time_s : null;
		// First point: compare to next
		if (prev === null && next !== null) return curr <= next ? -14 : 22;
		// Last point: compare to prev
		if (next === null && prev !== null) return curr <= prev ? -14 : 22;
		// Single point
		if (prev === null && next === null) return -14;
		// If slower than both neighbors (valley on chart), place label below
		if (curr > prev && curr > next) return 22;
		// Otherwise place above
		return -14;
	}

	// Determine text color for team color badges
	function textOnColor(hex) {
		if (!hex || hex.length < 7) return '#fff';
		const r = parseInt(hex.slice(1, 3), 16);
		const g = parseInt(hex.slice(3, 5), 16);
		const b = parseInt(hex.slice(5, 7), 16);
		const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
		return luminance > 0.5 ? '#000' : '#fff';
	}

	function compoundColor(compound) {
		return COMPOUND_COLORS[compound] || '#888';
	}

	// Check if a sector time is the best across all attempts for that sector
	function isBestSector(attempt, sector) {
		if (!bestSectors) return false;
		const best = bestSectors[sector];
		if (!best || !best.attempt) return false;
		return (
			best.attempt.attempt_number === attempt.attempt_number &&
			best.attempt.session === attempt.session
		);
	}
</script>

<svelte:head>
	<title>{driverCode} {$t('qualifying.title')} - {raceInfo.name} - RaceRead</title>
</svelte:head>

<section class="quali-detail">
	<!-- Back link -->
	<a href="/race/{raceId}" class="quali-detail__back">
		<span class="quali-detail__back-arrow">&larr;</span>
		{raceInfo.name}
	</a>

	{#if !driverData}
		<!-- Driver not found -->
		<div class="quali-detail__empty">
			<p>{$t('common.no_data')}</p>
		</div>
	{:else}
		<!-- Driver header -->
		<div class="quali-detail__header">
			<div class="quali-detail__identity">
				<span
					class="quali-detail__badge"
					style="background: {teamColor}; color: {textOnColor(teamColor)}"
				>
					{driverCode}
				</span>
				<div class="quali-detail__info">
					<span class="quali-detail__team">{driverData.team}</span>
					<span class="quali-detail__position">
						P{driverData.position}
						{#if driverData.gap_to_pole === 0}
							- {$t('qualifying.pole')}
						{:else if driverData.gap_to_pole != null}
							- +{driverData.gap_to_pole.toFixed(3)}s
						{/if}
					</span>
				</div>
			</div>
			<div class="quali-detail__best-time">
				<span class="quali-detail__best-label">{$t('charts.best_lap')}</span>
				<span class="quali-detail__best-value">
					{driverData.q3 || driverData.q2 || driverData.q1 || '-'}
				</span>
			</div>
		</div>

		{#if !hasAttempts}
			<!-- No attempt data available -->
			<div class="quali-detail__no-attempts">
				<div class="chart-card">
					<div class="chart-card__header">
						<span class="chart-card__title">{$t('qualifying_detail.attempts')}</span>
					</div>
					<p class="quali-detail__no-data-msg">{$t('qualifying_detail.no_attempts')}</p>
				</div>
			</div>
		{:else}
			<!-- Attempts table -->
			<div class="chart-card">
				<div class="chart-card__header">
					<span class="chart-card__title">{$t('qualifying_detail.attempts')}</span>
				</div>
				<div class="quali-detail__table-wrap">
					<table class="attempts-table">
						<thead>
							<tr>
								<th class="col-session">{$t('qualifying_detail.session_col')}</th>
								<th class="col-attempt">#</th>
								<th class="col-time">{$t('qualifying_detail.time')}</th>
								<th class="col-sector">S1</th>
								<th class="col-sector">S2</th>
								<th class="col-sector">S3</th>
								<th class="col-compound">{$t('common.compound')}</th>
								<th class="col-status">{$t('qualifying_detail.status')}</th>
							</tr>
						</thead>
						<tbody>
							{#each activeSessions as session}
								{#each attemptsBySession[session] as attempt, idx}
									{@const isDeleted = attempt.is_deleted}
									{@const isPB = attempt.is_personal_best}
									<tr
										class:row--deleted={isDeleted}
										class:row--pb={isPB && !isDeleted}
									>
										<!-- Show session label only for first row in group -->
										<td class="col-session">
											{#if idx === 0}
												<span class="session-label">{session}</span>
											{/if}
										</td>
										<td class="col-attempt">{attempt.attempt_number}</td>
										<td class="col-time" class:strikethrough={isDeleted}>
											{attempt.time_str || formatLapTime(attempt.time_s)}
										</td>
										<td
											class="col-sector"
											class:strikethrough={isDeleted}
											class:best-sector={!isDeleted && isBestSector(attempt, 's1')}
										>
											{attempt.s1 != null ? attempt.s1.toFixed(3) : '-'}
										</td>
										<td
											class="col-sector"
											class:strikethrough={isDeleted}
											class:best-sector={!isDeleted && isBestSector(attempt, 's2')}
										>
											{attempt.s2 != null ? attempt.s2.toFixed(3) : '-'}
										</td>
										<td
											class="col-sector"
											class:strikethrough={isDeleted}
											class:best-sector={!isDeleted && isBestSector(attempt, 's3')}
										>
											{attempt.s3 != null ? attempt.s3.toFixed(3) : '-'}
										</td>
										<td class="col-compound">
											{#if attempt.compound}
												<span
													class="compound-dot"
													style="background: {compoundColor(attempt.compound)}"
												></span>
												<span class="compound-label">{attempt.compound}</span>
											{:else}
												-
											{/if}
										</td>
										<td class="col-status">
											{#if isDeleted}
												<span class="status-deleted">{$t('qualifying_detail.deleted')}</span>
											{:else if isPB}
												<span class="status-pb">PB</span>
											{:else}
												<span class="status-empty">-</span>
											{/if}
										</td>
									</tr>
								{/each}
							{/each}
						</tbody>
					</table>
				</div>
			</div>

			<!-- Improvement chart -->
			{#if chartAttempts.length > 1}
				<div class="chart-card">
					<div class="chart-card__header">
						<span class="chart-card__title">{$t('qualifying_detail.improvement')}</span>
					</div>
					<svg viewBox="0 0 {chartW} {chartH}" class="improvement-chart" role="img" aria-label={$t('qualifying_detail.improvement')}>
						<!-- Y axis grid lines -->
						{#each Array(yTicks) as _, i}
							{@const tickVal = timeRange.min + ((timeRange.max - timeRange.min) / (yTicks - 1)) * i}
							{@const tickY = yScale(tickVal)}
							<line
								x1={margin.left}
								y1={tickY}
								x2={chartW - margin.right}
								y2={tickY}
								stroke="var(--border)"
								stroke-opacity="0.4"
							/>
							<text
								x={margin.left - 8}
								y={tickY + 4}
								fill="var(--text-muted)"
								font-size="10"
								text-anchor="end"
								font-family="var(--font-mono)"
							>
								{formatLapTime(tickVal)}
							</text>
						{/each}

						<!-- Session separators -->
						{#each sessionSeparators as sep}
							<line
								x1={sep.x}
								y1={margin.top}
								x2={sep.x}
								y2={chartH - margin.bottom}
								stroke="var(--text-muted)"
								stroke-opacity="0.3"
								stroke-dasharray="4 3"
							/>
							<text
								x={sep.x}
								y={chartH - margin.bottom + 16}
								fill="var(--text-muted)"
								font-size="10"
								text-anchor="middle"
								font-family="var(--font-mono)"
							>
								{sep.label}
							</text>
						{/each}

						<!-- First session label -->
						{#if chartAttempts.length > 0}
							<text
								x={xScale(0)}
								y={chartH - margin.bottom + 16}
								fill="var(--text-muted)"
								font-size="10"
								text-anchor="middle"
								font-family="var(--font-mono)"
							>
								{chartAttempts[0].session}
							</text>
						{/if}

						<!-- Line -->
						<path
							d={linePath}
							fill="none"
							stroke={teamColor}
							stroke-width="2.5"
							stroke-linejoin="round"
							stroke-linecap="round"
						/>

						<!-- Data points -->
						{#each chartAttempts as a, i}
							<circle
								cx={xScale(i)}
								cy={yScale(a.time_s)}
								r={a.is_personal_best ? 6 : 4.5}
								fill={a.is_personal_best ? '#22C55E' : teamColor}
								stroke="var(--bg-primary)"
								stroke-width="1.5"
							/>
							<!-- Time label on hover-sized target -->
							<text
								x={xScale(i)}
								y={yScale(a.time_s) + labelYOffset(i)}
								fill="var(--text-secondary)"
								font-size="10"
								text-anchor="middle"
								font-family="var(--font-mono)"
							>
								{formatLapTime(a.time_s)}
							</text>
						{/each}

						<!-- X axis label -->
						<text
							x={chartW / 2}
							y={chartH - 4}
							fill="var(--text-muted)"
							font-size="10"
							text-anchor="middle"
							font-family="var(--font-mono)"
						>
							{$t('qualifying_detail.attempt_number')}
						</text>
					</svg>
				</div>
			{/if}

			<!-- Best sectors summary -->
			{#if bestSectors && bestSectors.s1 && bestSectors.s2 && bestSectors.s3}
				<div class="chart-card">
					<div class="chart-card__header">
						<span class="chart-card__title">{$t('qualifying_detail.best_sectors')}</span>
					</div>
					<div class="best-sectors">
						{#each [['S1', bestSectors.s1], ['S2', bestSectors.s2], ['S3', bestSectors.s3]] as [label, data]}
							<div class="best-sector-card">
								<span class="best-sector-card__label">{label}</span>
								<span class="best-sector-card__time">{data.value.toFixed(3)}s</span>
								<span class="best-sector-card__source">
									{data.attempt.session} - #{data.attempt.attempt_number}
								</span>
							</div>
						{/each}
						{#if theoreticalBest}
							{@const actualBest = driverData.q3_s || driverData.q2_s || driverData.q1_s}
							<div class="best-sector-card best-sector-card--total">
								<span class="best-sector-card__label">{$t('qualifying.theoretical_best')}</span>
								<span class="best-sector-card__time">{formatLapTime(theoreticalBest)}</span>
								{#if actualBest}
									{@const delta = actualBest - theoreticalBest}
									<span class="best-sector-card__delta">
										+{delta.toFixed(3)}s {$t('qualifying_detail.vs_actual')}
									</span>
								{/if}
							</div>
						{/if}
					</div>
				</div>
			{/if}

			<!-- Animate compare -->
			{#if otherDrivers.length > 0}
				<div class="chart-card">
					<div class="chart-card__header">
						<span class="chart-card__title">{$t('qualifying.animate_title')}</span>
					</div>
					<div class="animate-compare">
						<span class="animate-compare__label">{driverCode} {$t('charts.vs')}</span>
						<select class="animate-compare__select" bind:value={compareTarget}>
							<option value="">{$t('charts.select_drivers')}</option>
							{#each otherDrivers as d}
								{@const dColor = TEAM_COLORS[d.team] || '#888'}
								<option value={d.driver}>P{d.position} - {d.driver} ({d.team})</option>
							{/each}
						</select>
						{#if compareTarget}
							<a
								href="/race/{raceId}/qualifying/animate/{driverCode.toLowerCase()}/{compareTarget.toLowerCase()}"
								class="animate-compare__btn"
							>
								{$t('qualifying.play')} ▶
							</a>
						{/if}
					</div>
				</div>
			{/if}
		{/if}
	{/if}
</section>

<style>
	.quali-detail {
		padding-top: var(--space-md);
		display: flex;
		flex-direction: column;
		gap: var(--space-lg);
	}

	/* Back link */
	.quali-detail__back {
		font-family: var(--font-mono);
		font-size: var(--font-size-small);
		color: var(--text-muted);
		text-decoration: none;
		display: inline-flex;
		align-items: center;
		gap: var(--space-xs);
		transition: color 0.15s;
	}
	.quali-detail__back:hover {
		color: var(--text-secondary);
	}
	.quali-detail__back-arrow {
		font-size: 14px;
	}

	/* Driver header */
	.quali-detail__header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-md);
		flex-wrap: wrap;
	}
	.quali-detail__identity {
		display: flex;
		align-items: center;
		gap: var(--space-md);
	}
	.quali-detail__badge {
		font-family: var(--font-mono);
		font-size: 22px;
		font-weight: 700;
		padding: 6px 16px;
		border-radius: 6px;
		letter-spacing: 0.04em;
	}
	.quali-detail__info {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.quali-detail__team {
		font-family: var(--font-sans);
		font-size: 14px;
		color: var(--text-secondary);
	}
	.quali-detail__position {
		font-family: var(--font-mono);
		font-size: 13px;
		color: var(--text-muted);
	}
	.quali-detail__best-time {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 2px;
	}
	.quali-detail__best-label {
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.quali-detail__best-value {
		font-family: var(--font-mono);
		font-size: 20px;
		font-weight: 700;
		color: var(--text-primary);
		font-variant-numeric: tabular-nums;
	}

	/* Empty / no data states */
	.quali-detail__empty,
	.quali-detail__no-attempts {
		width: 100%;
	}
	.quali-detail__no-data-msg {
		font-family: var(--font-mono);
		font-size: 13px;
		color: var(--text-muted);
		padding: var(--space-lg);
		text-align: center;
	}

	/* Attempts table */
	.quali-detail__table-wrap {
		overflow-x: auto;
	}
	.attempts-table {
		width: 100%;
		border-collapse: collapse;
	}
	.attempts-table th,
	.attempts-table td {
		font-family: var(--font-mono);
		font-size: 12px;
		padding: 6px 10px;
		white-space: nowrap;
		text-align: left;
	}
	.attempts-table th {
		font-size: 11px;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding-bottom: 8px;
		border-bottom: 1px solid var(--border);
	}
	.attempts-table td {
		border-bottom: 1px solid rgba(255, 255, 255, 0.04);
		font-variant-numeric: tabular-nums;
	}

	.col-session {
		width: 50px;
	}
	.session-label {
		font-weight: 700;
		font-size: 11px;
		color: var(--text-secondary);
		background: var(--bg-secondary);
		padding: 2px 6px;
		border-radius: 3px;
	}
	.col-attempt {
		width: 30px;
		text-align: center;
		color: var(--text-muted);
	}
	.col-time {
		text-align: right;
		font-weight: 600;
	}
	.col-sector {
		text-align: right;
		color: var(--text-secondary);
	}
	.col-compound {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.col-status {
		text-align: center;
		width: 60px;
	}

	/* Row states */
	.row--deleted td {
		background: rgba(239, 68, 68, 0.06);
		color: var(--text-muted);
	}
	.row--pb td {
		background: rgba(34, 197, 94, 0.06);
	}

	.strikethrough {
		text-decoration: line-through;
		opacity: 0.5;
	}
	.best-sector {
		color: #22C55E;
		font-weight: 700;
	}

	.compound-dot {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.compound-label {
		font-size: 10px;
		color: var(--text-muted);
		text-transform: uppercase;
	}

	.status-deleted {
		font-size: 9px;
		font-weight: 600;
		color: #EF4444;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}
	.status-pb {
		font-size: 9px;
		font-weight: 700;
		color: #22C55E;
		letter-spacing: 0.05em;
	}
	.status-empty {
		color: var(--text-muted);
		opacity: 0.3;
	}

	/* Improvement chart */
	.improvement-chart {
		width: 100%;
		max-height: 280px;
	}

	/* Best sectors summary */
	.best-sectors {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
		gap: var(--space-md);
		padding: var(--space-sm) 0;
	}
	.best-sector-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 4px;
		padding: var(--space-md);
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
	}
	.best-sector-card--total {
		border-color: rgba(34, 197, 94, 0.3);
		background: rgba(34, 197, 94, 0.04);
	}
	.best-sector-card__label {
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 600;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.best-sector-card__time {
		font-family: var(--font-mono);
		font-size: 18px;
		font-weight: 700;
		color: var(--text-primary);
		font-variant-numeric: tabular-nums;
	}
	.best-sector-card__source {
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--text-muted);
	}
	.best-sector-card__delta {
		font-family: var(--font-mono);
		font-size: 10px;
		color: #F59E0B;
	}

	/* Animate compare */
	.animate-compare {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		padding: var(--space-sm) 0;
		flex-wrap: wrap;
	}
	.animate-compare__label {
		font-family: var(--font-mono);
		font-size: 13px;
		font-weight: 600;
		color: var(--text-secondary);
	}
	.animate-compare__select {
		font-family: var(--font-mono);
		font-size: 12px;
		padding: 5px 8px;
		background: var(--bg-primary);
		color: var(--text-primary);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		min-width: 180px;
	}
	.animate-compare__btn {
		font-family: var(--font-mono);
		font-size: 12px;
		font-weight: 600;
		padding: 5px 14px;
		background: var(--accent);
		color: #fff;
		border: none;
		border-radius: var(--radius-sm);
		text-decoration: none;
		cursor: pointer;
		transition: opacity 0.15s;
	}
	.animate-compare__btn:hover {
		opacity: 0.85;
	}

	/* Responsive */
	@media (max-width: 768px) {
		.quali-detail__header {
			flex-direction: column;
			align-items: flex-start;
		}
		.quali-detail__best-time {
			align-items: flex-start;
		}
		.quali-detail__badge {
			font-size: 18px;
			padding: 4px 12px;
		}
		.best-sectors {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	@media (max-width: 480px) {
		.quali-detail__badge {
			font-size: 16px;
		}
		.quali-detail__best-value {
			font-size: 16px;
		}
		.best-sectors {
			grid-template-columns: 1fr;
		}
		.attempts-table th,
		.attempts-table td {
			padding: 5px 6px;
			font-size: 11px;
		}
	}
</style>
