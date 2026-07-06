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
			const { toPng } = await import('html-to-image');
			const url = await toPng(el, {
				backgroundColor: '#0F1117',
				pixelRatio: 2,
				filter: (node) => !node.classList?.contains('export-btn'),
			});
			const a = document.createElement('a');
			a.href = url;
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
		font-size: 9px;
		letter-spacing: 0.08em;
		padding: 3px 7px;
		background: var(--bg-primary, #0F1117);
		border: 1px solid var(--border, #2E3240);
		color: var(--text-muted, #7D8794);
		cursor: pointer;
		opacity: 0.45;
		transition: opacity 0.15s, color 0.15s, border-color 0.15s;
	}
	.export-btn:hover,
	.export-btn:focus-visible {
		opacity: 1;
		color: var(--text-primary, #E8E8ED);
		border-color: var(--text-muted, #7D8794);
	}
	.export-btn:disabled {
		cursor: wait;
	}
</style>
