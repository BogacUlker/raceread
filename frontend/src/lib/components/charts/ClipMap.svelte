<!--
	Clip Map - the circuit outline painted by how often the whole field
	hits the clip limiter at each point of the lap (server-aggregated).
-->
<script>
	import { t } from '$lib/i18n/index.js';
	import InferredBadge from '$lib/components/ui/InferredBadge.svelte';
	import { api } from '$lib/api.js';

	let { raceId, circuit = null, confidence = null } = $props();

	let clipData = $state(null);
	let failed = $state(false);
	$effect(() => {
		if (!raceId) return;
		api(`/api/races/${raceId}/energy/clipmap`)
			.then((d) => { clipData = d; })
			.catch(() => { failed = true; });
	});

	let outline = $derived(circuit?.outline || []);

	// normalize outline into a 500x440 viewBox
	let pts = $derived.by(() => {
		if (!outline.length) return [];
		const xs = outline.map((p) => p.x), ys = outline.map((p) => p.y);
		const minX = Math.min(...xs), maxX = Math.max(...xs);
		const minY = Math.min(...ys), maxY = Math.max(...ys);
		const w = maxX - minX || 1, hgt = maxY - minY || 1;
		const s = Math.min(440 / w, 380 / hgt);
		return outline.map((p) => ({
			x: (p.x - minX) * s + (500 - w * s) / 2,
			y: (p.y - minY) * s + (420 - hgt * s) / 2,
		}));
	});

	let maxShare = $derived(clipData ? Math.max(0.02, ...clipData.clip_share) : 1);

	function segColor(i) {
		if (!clipData) return 'var(--border)';
		const bin = Math.min(clipData.bins - 1, Math.floor((i / pts.length) * clipData.bins));
		const k = Math.min(1, clipData.clip_share[bin] / maxShare);
		// dark border color -> amber
		const from = [46, 50, 64], to = [245, 158, 11];
		const c = from.map((f, j) => Math.round(f + (to[j] - f) * k));
		return `rgb(${c[0]},${c[1]},${c[2]})`;
	}
	function segWidth(i) {
		if (!clipData) return 3;
		const bin = Math.min(clipData.bins - 1, Math.floor((i / pts.length) * clipData.bins));
		return 3 + (clipData.clip_share[bin] / maxShare) * 4;
	}
</script>

<div class="chart-card">
	<div class="chart-card__header">
		<span class="chart-card__title">{$t('energy.clipmap')}</span>
		<InferredBadge {confidence} />
	</div>
	{#if pts.length}
		<svg viewBox="0 0 500 440" class="cm-svg" role="img" aria-label={$t('energy.clipmap')}>
			{#each pts as p, i}
				{@const q = pts[(i + 1) % pts.length]}
				<line x1={p.x} y1={p.y} x2={q.x} y2={q.y}
					stroke={segColor(i)} stroke-width={segWidth(i)} stroke-linecap="round" />
			{/each}
		</svg>
		<div class="cm-legend">
			<span class="cm-legend__label">{$t('energy.clip_low')}</span>
			<span class="cm-grad"></span>
			<span class="cm-legend__label">{$t('energy.clip_high')} ({(maxShare * 100).toFixed(0)}%)</span>
		</div>
		<p class="cm-note">{$t('energy.clipmap_note')}</p>
	{:else if failed}
		<div class="cm-empty">{$t('common.no_data')}</div>
	{:else}
		<div class="cm-empty">{$t('common.loading')}</div>
	{/if}
</div>

<style>
	.cm-svg { width: 100%; max-height: 380px; height: auto; display: block; }
	.cm-legend { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
	.cm-legend__label { font-family: var(--font-mono); font-size: 9.5px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; }
	.cm-grad { flex: 0 0 120px; height: 6px; background: linear-gradient(90deg, var(--border), #F59E0B); }
	.cm-note { margin-top: 8px; font-size: 12px; line-height: 1.55; color: var(--text-muted); max-width: 60ch; }
	.cm-empty { padding: 3rem; text-align: center; font-family: var(--font-mono); font-size: 12px; color: var(--text-muted); }
</style>
