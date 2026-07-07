<script>
	import { t } from '$lib/i18n/index.js';

	/** @type {{ confidence?: number | null }} */
	let { confidence = null } = $props();

	let tip = $derived(
		confidence != null
			? `Energy states are inferred from public telemetry. Validation confidence for this race: ${Math.round(confidence)}/100 - see How It Works.`
			: undefined
	);
</script>

<a href="/methodology" class="inferred-badge" title={tip}>
	{$t('charts.inferred')}{#if confidence != null}<span class="inferred-badge__score">{Math.round(confidence)}</span>{/if}
</a>

<style>
	.inferred-badge {
		display: inline-block;
		font-family: var(--font-mono);
		font-size: 9.5px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		background: var(--energy-deploy);
		color: #000;
		padding: 1px 6px;
		border-radius: 3px;
		line-height: 1.4;
		vertical-align: middle;
		cursor: pointer;
		text-decoration: none;
	}
	.inferred-badge:hover { filter: brightness(1.12); text-decoration: none; }
	.inferred-badge__score {
		margin-left: 5px;
		padding-left: 5px;
		border-left: 1px solid rgba(0, 0, 0, 0.35);
		font-weight: 700;
	}
</style>
