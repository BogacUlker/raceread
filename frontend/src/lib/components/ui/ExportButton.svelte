<!--
	Exports a DOM node (chart section) as a PNG with a RaceRead footer stamp.
-->
<script>
	let { target, filename = 'raceread-chart' } = $props();
	let busy = $state(false);

	async function exportPng() {
		const el = document.querySelector(target);
		if (!el || busy) return;
		busy = true;
		try {
			// canvas can't resolve CSS var(); read the tokens at export time
			const css = getComputedStyle(document.documentElement);
			const bg = css.getPropertyValue('--bg-primary').trim() || '#15151E';
			const red = css.getPropertyValue('--accent').trim() || '#E10600';
			const { toCanvas } = await import('html-to-image');
			const canvas = await toCanvas(el, {
				backgroundColor: bg,
				pixelRatio: 2,
				filter: (node) => !node.classList?.contains('export-btn'),
				// content-visibility:auto leaves offscreen-optimized children
				// empty inside the clone - force everything visible for export
				style: { contentVisibility: 'visible', containIntrinsicSize: 'none' },
			});
			// broadcast watermark: red RACE chip + READ.APP, bottom right
			const ctx = canvas.getContext('2d');
			const k = 2; // pixelRatio
			ctx.font = `900 italic ${12 * k}px 'Titillium Web', sans-serif`;
			ctx.textBaseline = 'alphabetic';
			const w1 = ctx.measureText('RACE').width;
			const w2 = ctx.measureText('READ.APP').width;
			const pad = 6 * k;
			const x = canvas.width - (w1 + w2 + pad * 3) - 10 * k;
			const y = canvas.height - 11 * k;
			ctx.fillStyle = red;
			ctx.fillRect(x, y - 13 * k, w1 + pad * 2, 19 * k);
			ctx.fillStyle = 'rgba(0,0,0,.82)';
			ctx.fillRect(x + w1 + pad * 2, y - 13 * k, w2 + pad * 2, 19 * k);
			ctx.fillStyle = '#fff';
			ctx.fillText('RACE', x + pad, y);
			ctx.fillText('READ.APP', x + w1 + pad * 3, y);
			const a = document.createElement('a');
			a.href = canvas.toDataURL('image/png');
			a.download = filename + '.png';
			a.click();
		} catch (e) {
			console.error('PNG export failed:', e);
		}
		busy = false;
	}
</script>

<button class="export-btn" onclick={exportPng} disabled={busy} aria-label="Export chart as PNG" title="Export as PNG">
	{busy ? '...' : 'PNG'}
	<svg width="10" height="10" viewBox="0 0 12 12" fill="none" aria-hidden="true">
		<path d="M6 1v7M3 5.5L6 8.5 9 5.5M2 10.5h8" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
	</svg>
</button>

<style>
	.export-btn {
		position: absolute;
		top: 6px;
		right: 6px;
		z-index: 6;
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font-family: var(--font-mono);
		font-size: 9.5px;
		letter-spacing: 0.08em;
		padding: 3px 7px;
		background: var(--bg-primary);
		border: 1px solid var(--border);
		color: var(--text-muted);
		cursor: pointer;
		opacity: 0.45;
		transition: opacity 0.15s, color 0.15s, border-color 0.15s;
	}
	.export-btn:hover,
	.export-btn:focus-visible {
		opacity: 1;
		color: var(--text-primary);
		border-color: var(--text-muted);
	}
	.export-btn:disabled {
		cursor: wait;
	}
</style>
