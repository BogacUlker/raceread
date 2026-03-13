<script>
	import { t } from '$lib/i18n/index.js';

	let { data } = $props();
	let races = $derived(data.races);
</script>

<svelte:head>
	<title>RaceRead</title>
</svelte:head>

<section class="home">
	<div class="home__hero">
		<h1 class="home__title">{$t('home.title')}</h1>
		<p class="home__subtitle">{$t('home.subtitle')}</p>
	</div>

	<h2 class="home__section-title">{$t('home.select_race')}</h2>

	<div class="race-grid">
		{#each races as race}
			<a href="/race/{race.id}" class="race-card">
				<div class="race-card__header">
					<span class="race-card__date">{race.date}</span>
				</div>
				<h3 class="race-card__name">{race.name}</h3>
				<div class="race-card__details">
					<span class="race-card__circuit">{race.circuit}</span>
					<span class="race-card__sep">-</span>
					<span class="race-card__laps">{race.total_laps} {$t('race.laps')}</span>
				</div>
				<div class="race-card__winner">
					<span class="race-card__winner-label">{$t('race.winner')}</span>
					<span class="race-card__winner-name">{race.winner}</span>
				</div>
			</a>
		{/each}
	</div>
</section>

<style>
	.home {
		padding-top: var(--space-xl);
	}
	.home__hero {
		margin-bottom: var(--space-xl);
	}
	.home__title {
		font-family: var(--font-mono);
		font-size: 32px;
		font-weight: 700;
		letter-spacing: -0.03em;
		margin-bottom: var(--space-xs);
	}
	.home__subtitle {
		font-size: 15px;
		color: var(--text-secondary);
	}
	.home__section-title {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: var(--space-md);
	}
	.race-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: var(--space-md);
	}
	.race-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--space-lg);
		text-decoration: none;
		color: inherit;
		transition: border-color 0.2s, transform 0.15s;
	}
	.race-card:hover {
		border-color: var(--accent);
		transform: translateY(-2px);
		text-decoration: none;
	}
	.race-card__header {
		margin-bottom: var(--space-sm);
	}
	.race-card__date {
		font-family: var(--font-mono);
		font-size: 12px;
		color: var(--text-muted);
	}
	.race-card__name {
		font-size: 18px;
		font-weight: 600;
		margin-bottom: var(--space-sm);
	}
	.race-card__details {
		font-size: 13px;
		color: var(--text-secondary);
		margin-bottom: var(--space-md);
		display: flex;
		gap: var(--space-xs);
	}
	.race-card__winner {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
		padding-top: var(--space-sm);
		border-top: 1px solid var(--border);
	}
	.race-card__winner-label {
		font-size: 11px;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}
	.race-card__winner-name {
		font-family: var(--font-mono);
		font-size: 14px;
		font-weight: 600;
		color: var(--accent);
	}
</style>
