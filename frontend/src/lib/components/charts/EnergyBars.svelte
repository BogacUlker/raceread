<!--
	Energy Profile Bars - normalized stacked horizontal bars per driver.
	Pure HTML/CSS. Sorted by D/C ratio (rank from API).
	Click-to-select syncs EnergyTimeline. Hover syncs PaceChart.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS, ENERGY_COLORS } from '$lib/constants.js';
	import InferredBadge from '$lib/components/ui/InferredBadge.svelte';
	import { get } from 'svelte/store';
	import { hoveredDriver, selectedEnergyDriver } from '$lib/stores/race.js';
	import { formatPct } from '$lib/utils/format.js';

	/**
	 * @type {{ entries: Array<{driver: string, team: string, deploy_pct: number, harvest_pct: number, clip_pct: number, dc_ratio: number, rank: number}> }}
	 */
	let { entries } = $props();

	let sorted = $derived([...entries].sort((a, b) => a.rank - b.rank));

	function textOnColor(hex) {
		const r = parseInt(hex.slice(1, 3), 16);
		const g = parseInt(hex.slice(3, 5), 16);
		const b = parseInt(hex.slice(5, 7), 16);
		const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
		return luminance > 0.5 ? '#000' : '#fff';
	}

	let hovered = $state(null);
	let selectedDriver = $state(null);
	let tooltip = $state(null);
	let tooltipX = $state(0);
	let tooltipY = $state(0);

	hoveredDriver.subscribe(v => hovered = v);
	selectedEnergyDriver.subscribe(v => selectedDriver = v);

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

	function handleRowClick(entry) {
		selectedEnergyDriver.set(entry.driver);
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
		<span class="chart-card__title">{$t('charts.energy_bars')}</span>
		<InferredBadge />
	</div>

	<!-- Legend -->
	<div class="legend">
		<span class="legend__item">
			<span class="legend__dot" style="background: {ENERGY_COLORS.deploy}"></span>
			{$t('charts.deploy')}
		</span>
		<span class="legend__item">
			<span class="legend__dot" style="background: {ENERGY_COLORS.harvest}"></span>
			{$t('charts.harvest')}
		</span>
		<span class="legend__item">
			<span class="legend__dot" style="background: {ENERGY_COLORS.clip}"></span>
			{$t('charts.clip')}
		</span>
	</div>

	<div class="bars">
		{#each sorted as entry}
			{@const color = TEAM_COLORS[entry.team] || '#888'}
			{@const isHovered = hovered === entry.driver}
			{@const isSelected = selectedDriver === entry.driver}
			{@const isFaded = hovered && !isHovered}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<div
				class="bar-row"
				class:bar-row--faded={isFaded}
				class:bar-row--selected={isSelected}
				style="cursor: pointer;"
				onmouseenter={(e) => handleRowEnter(entry, e)}
				onmousemove={handleRowMove}
				onmouseleave={handleRowLeave}
				onclick={() => handleRowClick(entry)}
			>
				<span class="bar-row__driver" class:bar-row__driver--selected={isSelected} style="background: {color}; color: {textOnColor(color)}">{entry.driver}</span>
				<div class="bar-row__stack">
					<div
						class="segment"
						style="width: {entry.deploy_pct}%; background: {ENERGY_COLORS.deploy}"
					></div>
					<div
						class="segment"
						style="width: {entry.harvest_pct}%; background: {ENERGY_COLORS.harvest}"
					></div>
					<div
						class="segment"
						style="width: {entry.clip_pct}%; background: {ENERGY_COLORS.clip}"
					></div>
				</div>
				<span class="bar-row__ratio">
					{entry.dc_ratio.toFixed(2)}
				</span>
			</div>
		{/each}

		<!-- Floating tooltip -->
		{#if tooltip}
			{@const tx = tooltipX + 14}
			{@const ty = tooltipY - 60}
			<div
				class="energy-tooltip"
				style="left: {tx}px; top: {ty}px;"
			>
				<div class="energy-tooltip__header">{tooltip.driver}</div>
				<div class="energy-tooltip__row">
					<span class="energy-tooltip__dot" style="background: {ENERGY_COLORS.deploy}"></span>
					{$t('charts.deploy')}: {formatPct(tooltip.deploy_pct)}
				</div>
				<div class="energy-tooltip__row">
					<span class="energy-tooltip__dot" style="background: {ENERGY_COLORS.harvest}"></span>
					{$t('charts.harvest')}: {formatPct(tooltip.harvest_pct)}
				</div>
				<div class="energy-tooltip__row">
					<span class="energy-tooltip__dot" style="background: {ENERGY_COLORS.clip}"></span>
					{$t('charts.clip')}: {formatPct(tooltip.clip_pct)}
				</div>
				<div class="energy-tooltip__row">
					{$t('charts.dc_ratio')}: {tooltip.dc_ratio.toFixed(2)}
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
	.legend__dot {
		width: 8px;
		height: 8px;
		border-radius: 2px;
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
		border-left: 2px solid transparent;
	}
	.bar-row--faded {
		opacity: 0.5;
	}
	.bar-row--selected {
		border-left-color: transparent;
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
		border: 2px solid transparent;
		transition: border-color 0.15s, box-shadow 0.15s;
	}
	.bar-row__driver--selected {
		border-color: var(--accent);
		box-shadow: 0 0 6px rgba(226, 75, 74, 0.5);
	}
	.bar-row__stack {
		flex: 1;
		height: 22px;
		display: flex;
		border-radius: 3px;
		overflow: hidden;
		background: var(--bg-primary);
	}
	.segment {
		height: 100%;
		opacity: 0.8;
		transition: width 0.3s ease;
	}
	.bar-row:hover .segment {
		opacity: 1;
	}
	.bar-row__ratio {
		font-family: var(--font-mono);
		font-size: var(--font-size-compact);
		font-weight: 600;
		color: var(--text-secondary);
		width: 42px;
		text-align: right;
		flex-shrink: 0;
	}

	.energy-tooltip {
		position: absolute;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: 8px 10px;
		pointer-events: none;
		z-index: 20;
		min-width: 140px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
		font-family: var(--font-mono);
		font-size: 12px;
		color: var(--text-secondary);
	}
	.energy-tooltip__header {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 4px;
		padding-bottom: 4px;
		border-bottom: 1px solid var(--border);
	}
	.energy-tooltip__row {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 1px 0;
	}
	.energy-tooltip__dot {
		width: 6px;
		height: 6px;
		border-radius: 2px;
		flex-shrink: 0;
	}
</style>
