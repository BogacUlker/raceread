<script>
	import { TEAM_COLORS } from '$lib/constants.js';
	import { t } from '$lib/i18n/index.js';

	/**
	 * @type {{
	 *   drivers: Array<{driver: string, team: string}>,
	 *   selected: string[],
	 *   onchange: (selected: string[]) => void
	 * }}
	 */
	let { drivers, selected, onchange } = $props();

	function toggle(driver) {
		const next = selected.includes(driver)
			? selected.filter((d) => d !== driver)
			: [...selected, driver];
		onchange(next);
	}

	function selectAll() {
		onchange(drivers.map((d) => d.driver));
	}

	function deselectAll() {
		onchange([]);
	}
</script>

<div class="driver-filter">
	<div class="driver-filter__actions">
		<button class="filter-btn" onclick={selectAll}>{$t('filter.all_drivers')}</button>
		<button class="filter-btn" onclick={deselectAll}>Clear</button>
	</div>
	<div class="driver-filter__list">
		{#each drivers as { driver, team }}
			{@const color = TEAM_COLORS[team] || '#888'}
			<label class="driver-chip" class:active={selected.includes(driver)}>
				<span class="driver-chip__dot" style="background: {color}"></span>
				<span class="driver-chip__name">{driver}</span>
				<input
					type="checkbox"
					checked={selected.includes(driver)}
					onchange={() => toggle(driver)}
					hidden
				/>
			</label>
		{/each}
	</div>
</div>

<style>
	.driver-filter {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}
	.driver-filter__actions {
		display: flex;
		gap: var(--space-sm);
	}
	.filter-btn {
		font-family: var(--font-mono);
		font-size: 11px;
		padding: 2px 8px;
		background: transparent;
		color: var(--text-muted);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: all 0.15s;
	}
	.filter-btn:hover {
		color: var(--text-secondary);
		border-color: var(--text-muted);
	}
	.driver-filter__list {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.driver-chip {
		display: flex;
		align-items: center;
		gap: 5px;
		padding: 3px 10px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
		cursor: pointer;
		transition: all 0.15s;
		opacity: 0.45;
		background: transparent;
	}
	.driver-chip.active {
		opacity: 1;
		background: var(--bg-secondary);
		border-color: var(--text-muted);
	}
	.driver-chip__dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.driver-chip__name {
		font-family: var(--font-mono);
		font-size: 12px;
		font-weight: 500;
		color: var(--text-primary);
	}
</style>
