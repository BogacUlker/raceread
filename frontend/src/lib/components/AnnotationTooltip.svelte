<!--
	AnnotationTooltip - appears as hover tooltip on chart data points with annotations.
	Displays text_tr or text_en based on locale.
-->
<script>
	import { locale } from '$lib/i18n/index.js';
	import { ANNOTATION_COLORS } from '$lib/constants.js';

	/**
	 * @type {{
	 *   annotation: {driver: string, lap: number, chart_type: string, text_tr: string, text_en: string, category: string, severity: string} | null,
	 *   x: number,
	 *   y: number,
	 *   visible: boolean
	 * }}
	 */
	let { annotation = null, x = 0, y = 0, visible = false } = $props();

	let text = $derived(
		annotation
			? $locale === 'tr'
				? annotation.text_tr
				: annotation.text_en
			: ''
	);

	let borderColor = $derived(
		annotation ? ANNOTATION_COLORS[annotation.category] || '#888' : '#888'
	);
</script>

{#if visible && annotation}
	<div
		class="annotation-tooltip"
		style="left: {x}px; top: {y}px; border-left-color: {borderColor}"
	>
		<div class="annotation-tooltip__category">
			{annotation.category.replace('_', ' ')}
		</div>
		<div class="annotation-tooltip__text">{text}</div>
	</div>
{/if}

<style>
	.annotation-tooltip {
		position: absolute;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-left: 3px solid;
		border-radius: var(--radius-sm);
		padding: 8px 10px;
		pointer-events: none;
		z-index: 30;
		max-width: 260px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
		transform: translate(12px, -50%);
	}
	.annotation-tooltip__category {
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-muted);
		margin-bottom: 4px;
	}
	.annotation-tooltip__text {
		font-family: var(--font-mono);
		font-size: 13px;
		line-height: 1.5;
		color: var(--text-primary);
	}
</style>
