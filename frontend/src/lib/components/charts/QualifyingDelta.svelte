<!--
	Qualifying Delta - horizontal bars showing gap to pole.
	Three groups: Q3, Q2, Q1. Team-colored bars. Pole sitter gets "POLE" label.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS } from '$lib/constants.js';

	/** @type {{ drivers: Array<any> }} */
	let { drivers } = $props();

	// Split into groups
	let q3Drivers = $derived(drivers.filter((d) => d.q3_s != null));
	let q2Drivers = $derived(drivers.filter((d) => d.eliminated_in === 'Q2'));
	let q1Drivers = $derived(drivers.filter((d) => d.eliminated_in === 'Q1'));

	// Max gap for bar scaling
	let maxGap = $derived(
		Math.max(...drivers.map((d) => d.gap_to_pole ?? 0), 0.1)
	);

	function barWidth(gap) {
		if (gap == null || gap === 0 || maxGap === 0) return 0;
		return Math.min((gap / maxGap) * 100, 100);
	}

	let hovered = $state(null);
</script>

<div class="chart-card">
	<div class="chart-card__header">
		<span class="chart-card__title">{$t('qualifying.qualifying_delta')}</span>
	</div>

	<div class="delta-groups">
		<!-- Q3 group -->
		{#if q3Drivers.length > 0}
			<div class="delta-group">
				<div class="delta-group__label">Q3</div>
				{#each q3Drivers as d}
					{@const color = TEAM_COLORS[d.team] || '#888'}
					{@const isFaded = hovered && hovered !== d.driver}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div
						class="delta-row"
						class:delta-row--faded={isFaded}
						onmouseenter={() => hovered = d.driver}
						onmouseleave={() => hovered = null}
					>
						<span class="delta-row__driver" style="color: {color}">{d.driver}</span>
						<div class="delta-row__bar-area">
							{#if d.gap_to_pole === 0}
								<span class="pole-label">{$t('qualifying.pole')}</span>
							{:else}
								<div
									class="delta-row__bar"
									style="width: {barWidth(d.gap_to_pole)}%; background: {color}"
								></div>
							{/if}
						</div>
						<span class="delta-row__gap">
							{#if d.gap_to_pole === 0}
								-
							{:else}
								+{d.gap_to_pole.toFixed(3)}s
							{/if}
						</span>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Q2 group -->
		{#if q2Drivers.length > 0}
			<div class="delta-group">
				<div class="delta-group__label delta-group__label--q2">Q2</div>
				{#each q2Drivers as d}
					{@const color = TEAM_COLORS[d.team] || '#888'}
					{@const isFaded = hovered && hovered !== d.driver}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div
						class="delta-row"
						class:delta-row--faded={isFaded}
						onmouseenter={() => hovered = d.driver}
						onmouseleave={() => hovered = null}
					>
						<span class="delta-row__driver" style="color: {color}">{d.driver}</span>
						<div class="delta-row__bar-area">
							<div
								class="delta-row__bar"
								style="width: {barWidth(d.gap_to_pole)}%; background: {color}; opacity: 0.7"
							></div>
						</div>
						<span class="delta-row__gap">+{(d.gap_to_pole ?? 0).toFixed(3)}s</span>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Q1 group -->
		{#if q1Drivers.length > 0}
			<div class="delta-group">
				<div class="delta-group__label delta-group__label--q1">Q1</div>
				{#each q1Drivers as d}
					{@const color = TEAM_COLORS[d.team] || '#888'}
					{@const isFaded = hovered && hovered !== d.driver}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div
						class="delta-row"
						class:delta-row--faded={isFaded}
						onmouseenter={() => hovered = d.driver}
						onmouseleave={() => hovered = null}
					>
						<span class="delta-row__driver" style="color: {color}">{d.driver}</span>
						<div class="delta-row__bar-area">
							<div
								class="delta-row__bar"
								style="width: {barWidth(d.gap_to_pole)}%; background: {color}; opacity: 0.5"
							></div>
						</div>
						<span class="delta-row__gap">+{(d.gap_to_pole ?? 0).toFixed(3)}s</span>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>

<style>
	.delta-groups {
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
	}
	.delta-group {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.delta-group__label {
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 700;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.06em;
		padding-bottom: 4px;
		border-bottom: 1px solid var(--border);
	}
	.delta-group__label--q2 {
		color: #F59E0B;
	}
	.delta-group__label--q1 {
		color: #EF4444;
	}
	.delta-row {
		display: flex;
		align-items: center;
		gap: 10px;
		transition: opacity 0.15s;
		padding: 2px 0;
	}
	.delta-row--faded {
		opacity: 0.4;
	}
	.delta-row__driver {
		font-family: var(--font-mono);
		font-size: 13px;
		font-weight: 600;
		width: 36px;
		flex-shrink: 0;
	}
	.delta-row__bar-area {
		flex: 1;
		height: 18px;
		position: relative;
		display: flex;
		align-items: center;
	}
	.delta-row__bar {
		height: 100%;
		border-radius: 3px;
		min-width: 2px;
		transition: width 0.3s ease;
	}
	.pole-label {
		font-family: var(--font-mono);
		font-size: 10px;
		font-weight: 700;
		color: var(--accent);
		letter-spacing: 0.06em;
	}
	.delta-row__gap {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-secondary);
		width: 70px;
		text-align: right;
		flex-shrink: 0;
		font-variant-numeric: tabular-nums;
	}
</style>
