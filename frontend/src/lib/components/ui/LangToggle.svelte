<script>
	import { locale } from '$lib/i18n/index.js';

	function toggle() {
		locale.update((l) => (l === 'tr' ? 'en' : 'tr'));
	}
</script>

<button class="lang-toggle" onclick={toggle}>
	{$locale === 'tr' ? 'EN' : 'TR'}
</button>

<style>
	.lang-toggle {
		font-family: var(--font-mono);
		font-size: 12px;
		font-weight: 600;
		padding: 4px 10px;
		background: var(--bg-secondary);
		color: var(--text-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: all 0.15s ease;
	}
	.lang-toggle:hover {
		color: var(--text-primary);
		border-color: var(--text-secondary);
	}
</style>
