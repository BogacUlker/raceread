<script>
	import { t } from '$lib/i18n/index.js';
	import LangToggle from '$lib/components/ui/LangToggle.svelte';
</script>

<header class="header">
	<div class="header__inner">
		<a href="/" class="header__logo">
			<img src="/logo@2x.png" alt="RaceRead" class="header__logo-img" width="114" height="64" />
		</a>
		<nav class="header__nav">
			<a href="/" class="header__link">{$t('nav.home')}</a>
		</nav>
		<div class="header__actions">
			<LangToggle />
		</div>
	</div>
</header>

<style>
	.header {
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border);
		position: sticky;
		top: 0;
		z-index: 100;
	}
	.header__inner {
		max-width: 1400px;
		margin: 0 auto;
		padding: 0 var(--space-lg);
		height: 56px;
		display: flex;
		align-items: center;
		gap: var(--space-lg);
	}
	.header__logo {
		display: flex;
		align-items: center;
		text-decoration: none;
	}
	.header__logo-img {
		height: 54px;
		width: auto;
		display: block;
	}
	.header__nav {
		flex: 1;
		display: flex;
		gap: var(--space-md);
	}
	.header__link {
		font-size: 13px;
		color: var(--text-secondary);
		text-decoration: none;
		transition: color 0.15s;
	}
	.header__link:hover {
		color: var(--text-primary);
		text-decoration: none;
	}
	.header__actions {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
	}

	@media (max-width: 480px) {
		.header__inner {
			padding: 0 var(--space-md);
			height: 48px;
		}
		.header__logo-img {
			height: 42px;
		}
	}
</style>
