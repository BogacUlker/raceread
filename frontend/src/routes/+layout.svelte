<script>
	// Broadcast typography, self-hosted (no CDN)
	import '@fontsource/titillium-web/400.css';
	import '@fontsource/titillium-web/600.css';
	import '@fontsource/titillium-web/700.css';
	import '@fontsource/titillium-web/900.css';
	import '@fontsource/titillium-web/600-italic.css';
	import '@fontsource/titillium-web/700-italic.css';
	import '@fontsource/saira-condensed/400.css';
	import '@fontsource/saira-condensed/500.css';
	import '@fontsource/saira-condensed/600.css';
	import '@fontsource/saira-condensed/700.css';
	import '@fontsource/graduate/400.css';
	import '../app.css';
	import { page } from '$app/state';
	import Header from '$lib/components/layout/Header.svelte';
	import Footer from '$lib/components/layout/Footer.svelte';

	let { children, data } = $props();

	const DEFAULT_DESC = 'F1 post-race telemetry analysis with energy inference and AI-generated insights';
	let metaTitle = $derived(page.data?.metaTitle || 'RaceRead');
	let metaDesc = $derived(page.data?.metaDescription || DEFAULT_DESC);
	let ogUrl = $derived('https://raceread.app' + (page.url?.pathname || '/'));
</script>

<svelte:head>
	<meta name="description" content={metaDesc} />
	<meta property="og:title" content={metaTitle} />
	<meta property="og:description" content={metaDesc} />
	<meta property="og:type" content="website" />
	<meta property="og:url" content={ogUrl} />
	<meta property="og:image" content="https://raceread.app/og-image.png" />
	<meta property="og:image:width" content="1200" />
	<meta property="og:image:height" content="630" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content={metaTitle} />
	<meta name="twitter:description" content={metaDesc} />
	<meta name="twitter:image" content="https://raceread.app/og-image.png" />
</svelte:head>

<div class="app">
	<Header />
	<main class="main">
		{@render children()}
	</main>
	<Footer />
</div>

<style>
	.app {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}
	.main {
		flex: 1;
		max-width: 1600px;
		width: 100%;
		margin: 0 auto;
		padding: var(--space-lg);
	}
</style>
