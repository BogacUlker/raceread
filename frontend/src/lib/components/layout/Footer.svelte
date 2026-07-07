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
	<div class="footer__legal">
		<span>Data: <a href="https://github.com/theOehrly/Fast-F1" target="_blank" rel="noopener noreferrer">FastF1</a> &middot; <a href="https://github.com/jolpica/jolpica-f1" target="_blank" rel="noopener noreferrer">{$t('footer.jolpica')}</a> &middot; <a href="https://openf1.org" target="_blank" rel="noopener noreferrer">{$t('footer.openf1')}</a> &middot; <a href="https://github.com/bacinger/f1-circuits" target="_blank" rel="noopener noreferrer">{$t('footer.circuits')}</a> &middot; <a href="/methodology">{$t('footer.methodology')}</a></span>
		<p>{$t('footer.disclaimer')}</p>
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
		color: var(--text-secondary);
		font-family: var(--font-mono);
		text-decoration: none;
		transition: color 0.2s;
	}
	.footer__coffee:hover {
		color: var(--text-primary);
	}
	.footer__legal {
		max-width: 1400px;
		margin: 10px auto 0;
		font-family: var(--font-mono);
		font-size: 10px;
		line-height: 1.6;
		color: var(--text-muted);
	}
	.footer__legal a {
		color: var(--text-secondary);
		text-decoration: none;
	}
	.footer__legal a:hover {
		color: var(--text-primary);
	}
	.footer__legal p {
		margin-top: 2px;
	}
</style>
