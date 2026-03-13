<script>
	import { t } from '$lib/i18n/index.js';
</script>

<span class="inferred-badge">{$t('charts.inferred')}</span>

<style>
	.inferred-badge {
		display: inline-block;
		font-family: var(--font-mono);
		font-size: 9px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		background: var(--energy-deploy);
		color: #000;
		padding: 1px 6px;
		border-radius: 3px;
		line-height: 1.4;
		vertical-align: middle;
	}
</style>
