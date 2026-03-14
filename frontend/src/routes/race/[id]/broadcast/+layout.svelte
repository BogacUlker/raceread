<!--
	Broadcast layout - hides Header/Footer, full viewport overlay.
-->
<script>
	import { onMount } from 'svelte';

	let { children } = $props();

	onMount(() => {
		// Hide parent layout elements for full-screen experience
		document.body.classList.add('broadcast-active');
		return () => document.body.classList.remove('broadcast-active');
	});
</script>

<div class="broadcast-layout">
	{@render children()}
</div>

<style>
	.broadcast-layout {
		position: fixed;
		top: 0;
		left: 0;
		width: 100vw;
		height: 100vh;
		overflow: hidden;
		background: var(--bg-primary);
		color: var(--text-primary);
		z-index: 1000;
	}
	:global(body.broadcast-active) {
		overflow: hidden;
	}
</style>
