<script>
	import { t } from '$lib/i18n/index.js';
</script>

<div class="loading">
	<div class="spinner"></div>
	<span>{$t('common.loading')}</span>
</div>

<style>
	.loading {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-md);
		padding: var(--space-xl);
		color: var(--text-secondary);
		font-family: var(--font-mono);
		font-size: 13px;
	}
	.spinner {
		width: 24px;
		height: 24px;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
