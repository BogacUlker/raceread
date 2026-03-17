<script>
	import { t } from '$lib/i18n/index.js';
</script>

<footer class="footer">
	<div class="footer__inner">
		<span class="footer__text">RaceRead - {$t('footer.tagline')}</span>
		<div class="footer__right">
			<a href="https://buymeacoffee.com/bogaculker" target="_blank" rel="noopener noreferrer" class="footer__coffee">
				&#9749; {$t('footer.buy_coffee')}
			</a>
			<span class="footer__text">2026</span>
		</div>
	</div>
</footer>

<style>
	.footer {
		border-top: 1px solid var(--border);
		padding: var(--space-lg);
		margin-top: auto;
	}
	.footer__inner {
		max-width: 1400px;
		margin: 0 auto;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}
	.footer__right {
		display: flex;
		align-items: center;
		gap: var(--space-md);
	}
	.footer__text {
		font-size: 12px;
		color: var(--text-muted);
		font-family: var(--font-mono);
	}
	.footer__coffee {
		font-size: 11px;
		color: var(--text-muted);
		font-family: var(--font-mono);
		text-decoration: none;
		opacity: 0.7;
		transition: opacity 0.2s;
	}
	.footer__coffee:hover {
		opacity: 1;
		color: var(--text-secondary);
	}
</style>
