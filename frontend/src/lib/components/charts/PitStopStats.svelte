<!--
	Pit Stop Stats - horizontal bar chart showing pit stop time loss per driver.
	Segmented bars for individual stops. SC pits shown with lighter opacity + dashed border.
	Sorted by total time lost descending. Hover syncs with other charts.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS, COMPOUND_COLORS } from '$lib/constants.js';
	import { get } from 'svelte/store';
	import { hoveredDriver } from '$lib/stores/race.js';

	/** @type {{ data: { race_id: string, drivers: Array<{ driver: string, team: string, pits: Array<{ lap: number, time_loss_s: number, compound_from: string, compound_to: string, under_sc: boolean }>, total_time_lost_s: number, num_stops: number }> } }} */
	let { data } = $props();

	/** Map compound abbreviations to full names for COMPOUND_COLORS lookup */
	const COMPOUND_MAP = {
		S: 'SOFT',
		M: 'MEDIUM',
		H: 'HARD',
		I: 'INTERMEDIATE',
		W: 'WET'
	};

	/** Get full compound name from abbreviation */
	function compoundFull(abbr) {
		return COMPOUND_MAP[abbr] || abbr;
	}

	/** Get compound color from abbreviation */
	function compoundColor(abbr) {
		return COMPOUND_COLORS[compoundFull(abbr)] || '#888';
	}

	let sorted = $derived(
		[...(data?.drivers || [])].sort((a, b) => b.total_time_lost_s - a.total_time_lost_s)
	);

	let maxLoss = $derived(Math.max(...sorted.map((d) => d.total_time_lost_s), 1));

	function textOnColor(hex) {
		const r = parseInt(hex.slice(1, 3), 16);
		const g = parseInt(hex.slice(3, 5), 16);
		const b = parseInt(hex.slice(5, 7), 16);
		const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
		return luminance > 0.5 ? '#000' : '#fff';
	}

	let hovered = $state(null);
	let tooltip = $state(null);
	let tooltipX = $state(0);
	let tooltipY = $state(0);

	hoveredDriver.subscribe(v => hovered = v);

	function handleRowEnter(entry, e) {
		hovered = entry.driver;
		hoveredDriver.set(entry.driver);
		tooltip = entry;
		updateTooltipPos(e);
	}

	function handleRowMove(e) {
		updateTooltipPos(e);
	}

	function handleRowLeave() {
		hovered = null;
		hoveredDriver.set(null);
		tooltip = null;
	}

	function updateTooltipPos(e) {
		const container = e.currentTarget.closest('.bars');
		if (!container) return;
		const rect = container.getBoundingClientRect();
		tooltipX = e.clientX - rect.left;
		tooltipY = e.clientY - rect.top;
	}
</script>

<div class="chart-card">
	<div class="chart-card__header">
		<span class="chart-card__title">{$t('charts.pit_stops')}</span>
	</div>

	<!-- Legend -->
	<div class="legend">
		<span class="legend__item">
			<span class="legend__swatch legend__swatch--solid"></span>
			{$t('charts.pit_normal') || 'Normal pit'}
		</span>
		<span class="legend__item">
			<span class="legend__swatch legend__swatch--sc"></span>
			{$t('charts.pit_under_sc')}
		</span>
	</div>

	<div class="bars">
		{#each sorted as entry}
			{@const color = TEAM_COLORS[entry.team] || '#888'}
			{@const isHovered = hovered === entry.driver}
			{@const isFaded = hovered && !isHovered}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				class="bar-row"
				class:bar-row--faded={isFaded}
				onmouseenter={(e) => handleRowEnter(entry, e)}
				onmousemove={handleRowMove}
				onmouseleave={handleRowLeave}
			>
				<span
					class="bar-row__driver"
					style="background: {color}; color: {textOnColor(color)}"
				>
					{entry.driver}
				</span>
				<div
					class="bar-row__track"
					style="width: {(entry.total_time_lost_s / maxLoss) * 100}%"
				>
					{#each entry.pits as pit}
						<div
							class="segment"
							class:segment--sc={pit.under_sc}
							style="width: {((pit.time_loss_s ?? 0) / entry.total_time_lost_s) * 100}%; background: {color}"
						>
							<span class="segment__compound">
								{pit.compound_from}{' '}&rarr;{' '}{pit.compound_to}
							</span>
						</div>
					{/each}
				</div>
				<span class="bar-row__time">{entry.total_time_lost_s.toFixed(1)}s</span>
			</div>
		{/each}

		<!-- Floating tooltip -->
		{#if tooltip}
			{@const tx = tooltipX + 14}
			{@const ty = tooltipY - 60}
			{@const tColor = TEAM_COLORS[tooltip.team] || '#888'}
			<div class="pit-tooltip" style="left: {tx}px; top: {ty}px;">
				<div class="pit-tooltip__header">
					<span class="pit-tooltip__driver-badge" style="background: {tColor}; color: {textOnColor(tColor)}">{tooltip.driver}</span>
					<span class="pit-tooltip__stops">{tooltip.num_stops} {tooltip.num_stops === 1 ? 'stop' : 'stops'}</span>
				</div>
				{#each tooltip.pits as pit, i}
					<div class="pit-tooltip__row">
						<span class="pit-tooltip__label">
							Lap {pit.lap}:
						</span>
						<span class="pit-tooltip__compound">
							<span class="pit-tooltip__dot" style="background: {compoundColor(pit.compound_from)}"></span>
							{pit.compound_from}
							<span class="pit-tooltip__arrow">&rarr;</span>
							<span class="pit-tooltip__dot" style="background: {compoundColor(pit.compound_to)}"></span>
							{pit.compound_to}
						</span>
						<span class="pit-tooltip__time">{pit.time_loss_s != null ? pit.time_loss_s.toFixed(1) + 's' : '-'}</span>
					</div>
					{#if pit.under_sc}
						<div class="pit-tooltip__sc-note">{$t('charts.pit_under_sc')}</div>
					{/if}
				{/each}
				<div class="pit-tooltip__total">
					{$t('charts.total_loss')}: {tooltip.total_time_lost_s.toFixed(1)}s
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
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
		font-size: var(--font-size-small);
		color: var(--text-secondary);
	}
	.legend__swatch {
		width: 16px;
		height: 8px;
		border-radius: 2px;
	}
	.legend__swatch--solid {
		background: var(--text-secondary);
		opacity: 0.8;
	}
	.legend__swatch--sc {
		background: var(--text-secondary);
		opacity: 0.4;
		border-left: 2px dashed rgba(255, 255, 255, 0.5);
	}
	.bars {
		display: flex;
		flex-direction: column;
		gap: 8px;
		position: relative;
	}
	.bar-row {
		display: flex;
		align-items: center;
		gap: 10px;
		transition: opacity 0.15s;
		padding: 2px 0;
	}
	.bar-row--faded {
		opacity: 0.5;
	}
	.bar-row__driver {
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 700;
		width: 38px;
		flex-shrink: 0;
		text-align: center;
		padding: 2px 4px;
		border-radius: 3px;
		box-sizing: border-box;
	}
	.bar-row__track {
		height: 22px;
		display: flex;
		border-radius: 3px;
		overflow: hidden;
		background: var(--bg-primary);
		min-width: 4px;
		transition: width 0.3s ease;
	}
	.segment {
		height: 100%;
		opacity: 0.8;
		transition: width 0.3s ease;
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
	}
	.segment--sc {
		opacity: 0.4;
		border-left: 2px dashed rgba(255, 255, 255, 0.5);
	}
	.bar-row:hover .segment {
		opacity: 1;
	}
	.bar-row:hover .segment--sc {
		opacity: 0.55;
	}
	.segment__compound {
		font-family: var(--font-mono);
		font-size: 9px;
		font-weight: 600;
		color: rgba(255, 255, 255, 0.9);
		white-space: nowrap;
		pointer-events: none;
		text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
	}
	.bar-row__time {
		font-family: var(--font-mono);
		font-size: var(--font-size-compact);
		font-weight: 600;
		color: var(--text-secondary);
		width: 48px;
		text-align: right;
		flex-shrink: 0;
	}

	/* Tooltip */
	.pit-tooltip {
		position: absolute;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: 8px 10px;
		pointer-events: none;
		z-index: 20;
		min-width: 180px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
		font-family: var(--font-mono);
		font-size: 12px;
		color: var(--text-secondary);
	}
	.pit-tooltip__header {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-bottom: 6px;
		padding-bottom: 4px;
		border-bottom: 1px solid var(--border);
	}
	.pit-tooltip__driver-badge {
		font-size: 11px;
		font-weight: 700;
		padding: 1px 5px;
		border-radius: 3px;
	}
	.pit-tooltip__stops {
		font-size: 11px;
		color: var(--text-muted);
	}
	.pit-tooltip__row {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 2px 0;
	}
	.pit-tooltip__label {
		color: var(--text-muted);
		white-space: nowrap;
	}
	.pit-tooltip__compound {
		display: flex;
		align-items: center;
		gap: 3px;
		font-weight: 600;
	}
	.pit-tooltip__dot {
		width: 6px;
		height: 6px;
		border-radius: 2px;
		flex-shrink: 0;
	}
	.pit-tooltip__arrow {
		color: var(--text-muted);
		font-size: 10px;
	}
	.pit-tooltip__time {
		margin-left: auto;
		font-weight: 600;
		color: var(--text-primary);
	}
	.pit-tooltip__sc-note {
		font-size: 10px;
		color: var(--text-muted);
		font-style: italic;
		padding-left: 44px;
		margin-top: -2px;
	}
	.pit-tooltip__total {
		margin-top: 4px;
		padding-top: 4px;
		border-top: 1px solid var(--border);
		font-weight: 600;
		color: var(--text-primary);
	}
</style>
