<!--
	Session toggle bar - switches between Race and Qualifying views.
	Reads/writes the activeSession store.
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import { activeSession } from '$lib/stores/race.js';

	function switchTo(session) {
		activeSession.set(session);
	}
</script>

<div class="session-toggle">
	<button
		class="session-toggle__tab"
		class:active={$activeSession === 'race'}
		onclick={() => switchTo('race')}
	>
		{$t('session.race')}
	</button>
	<button
		class="session-toggle__tab"
		class:active={$activeSession === 'qualifying'}
		onclick={() => switchTo('qualifying')}
	>
		{$t('session.qualifying')}
	</button>
</div>

<style>
	.session-toggle {
		display: flex;
		gap: 0;
		border-bottom: 1px solid var(--border);
		margin-bottom: var(--space-md);
	}
	.session-toggle__tab {
		font-family: var(--font-mono);
		font-size: 14px;
		font-weight: 500;
		padding: 8px 20px;
		background: transparent;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--text-muted);
		cursor: pointer;
		transition: all 0.15s;
	}
	.session-toggle__tab:hover {
		color: var(--text-secondary);
	}
	.session-toggle__tab.active {
		color: var(--text-primary);
		border-bottom-color: var(--accent);
	}
</style>
