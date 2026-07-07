<!--
	Mini circuit silhouette by calendar code (AUS, GBR, ...).
	Paths pre-built from f1-circuits GeoJSON (MIT) - see
	backend/scripts/build_circuit_paths.py.
-->
<script>
	import paths from '$lib/data/circuit-paths.json';

	let { code = '', size = 44, stroke = 'var(--text-secondary)', width = 2.4, opacity = 0.6 } = $props();
	let d = $derived(paths[code] || null);
</script>

{#if d}
	<svg viewBox="0 0 100 100" width={size} height={size} aria-hidden="true" style="opacity:{opacity}">
		<path {d} fill="none" stroke={stroke} stroke-width={width * (100 / size)} stroke-linejoin="round" stroke-linecap="round" />
	</svg>
{/if}
