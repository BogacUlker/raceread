<script>
	import { t, locale } from '$lib/i18n/index.js';
	import { TEAM_COLORS, RACE_NAMES_TR, localizedRaceName } from '$lib/constants.js';
	import TrackSilhouette from '$lib/components/ui/TrackSilhouette.svelte';

	let { data } = $props();
	let races = $derived(data.races);
	let circuitOutline = $derived(data.circuitOutline || []);

	// Build SVG path from circuit outline
	let trackPath = $derived.by(() => {
		if (!circuitOutline.length) return '';
		const xs = circuitOutline.map(p => p.x), ys = circuitOutline.map(p => p.y);
		const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
		const w = maxX - minX || 1, h = maxY - minY || 1;
		return circuitOutline.map((p, i) => {
			const nx = ((p.x - minX) / w) * 460 + 20;
			const ny = ((p.y - minY) / h) * 420 + 20;
			return (i === 0 ? 'M' : 'L') + nx.toFixed(1) + ',' + ny.toFixed(1);
		}).join(' ') + ' Z';
	});


	const DRIVER_NAMES = {
		RUS: 'G. Russell', ANT: 'A. Antonelli', VER: 'M. Verstappen', HAD: 'I. Hadjar',
		HAM: 'L. Hamilton', LEC: 'C. Leclerc', NOR: 'L. Norris', PIA: 'O. Piastri',
		ALO: 'F. Alonso', STR: 'L. Stroll', GAS: 'P. Gasly', DOO: 'J. Doohan',
		ALB: 'A. Albon', SAI: 'C. Sainz', BEA: 'O. Bearman', OCO: 'E. Ocon',
		LAW: 'L. Lawson', TSU: 'Y. Tsunoda', HUL: 'N. Hulkenberg', BOR: 'G. Bortoleto',
		BOT: 'V. Bottas', COL: 'F. Colapinto', LIN: 'P. Lindblad', PER: 'S. Perez',
	};
	const DRIVER_TEAMS = {
		RUS: 'Mercedes', ANT: 'Mercedes', VER: 'Red Bull Racing', HAD: 'Red Bull Racing',
		HAM: 'Ferrari', LEC: 'Ferrari', NOR: 'McLaren', PIA: 'McLaren',
		ALO: 'Aston Martin', STR: 'Aston Martin', GAS: 'Alpine', DOO: 'Alpine',
		ALB: 'Williams', SAI: 'Williams', BEA: 'Haas F1 Team', OCO: 'Haas F1 Team',
		LAW: 'Racing Bulls', TSU: 'Racing Bulls', HUL: 'Audi', BOR: 'Audi',
		BOT: 'Cadillac', COL: 'Alpine', LIN: 'Racing Bulls', PER: 'Cadillac',
	};

	// Season calendar comes from /api/calendar (Jolpica-sourced, see
	// backend/scripts/fetch_calendar.py) - no more hardcoded schedule
	let calendar = $derived(data.calendar || []);
	let classics = $derived(data.classics || []);


	function raceName(name) {
		const n = localizedRaceName(name, $locale);
		// Uppercase with proper GRAND PRIX (not PRİX)
		const parts = n.split('Grand Prix');
		if (parts.length === 2) return parts[0].toLocaleUpperCase($locale === 'tr' ? 'tr' : 'en') + 'GRAND PRIX';
		return n.toUpperCase();
	}
	function calName(c) {
		if ($locale === 'tr' && RACE_NAMES_TR[c.full_name]) return RACE_NAMES_TR[c.full_name].replace('Grand Prix', 'GP');
		return c.name;
	}

	// Card extras now come from /api/races (weather.json + laps.json server-side)
	function fmtLapTime(s) {
		const m = Math.floor(s / 60);
		const sec = s % 60;
		return m + ':' + sec.toFixed(3).padStart(6, '0');
	}
	function computeExtras(race) {
		const sc = [];
		if (race.sc_periods) sc.push(race.sc_periods + ' SC');
		if (race.vsc_periods) sc.push(race.vsc_periods + ' VSC');
		return {
			temp: race.air_temp != null ? Math.round(race.air_temp) : null,
			rainfall: race.rainfall,
			fastest: race.fastest_lap_s ? fmtLapTime(race.fastest_lap_s) : null,
			fastestDriver: race.fastest_driver,
			sc: sc.length ? sc.join(' + ') : null,
		};
	}

	function getTeamColor(dc) { return TEAM_COLORS[DRIVER_TEAMS[dc]] || '#6B7280'; }
	function formatDate(d) { return new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: '2-digit' }).toUpperCase(); }
	function formatDateShort(d) { return new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }).toUpperCase(); }
	function isCompleted(c) { return races.some(r => r.date === c.date); }
	function getRaceId(c) { const r = races.find(r => r.date === c.date); return r ? r.id : null; }



	let hoveredCard = $state(null);
	let sidebarOpen = $state(false);    // mobile drawer
	let sidebarCollapsed = $state(true); // desktop collapse
</script>

<svelte:head>
	<title>RaceRead - {$t('home.tagline')}</title>
</svelte:head>

<div class="prv">

	<!-- NAV -->
	<nav class="prv-nav">
		<div class="prv-nav__inner">
			<div class="prv-nav__left">
				<button class="prv-nav__burger" aria-label="Menu" aria-expanded={sidebarOpen} onclick={() => sidebarOpen = !sidebarOpen}>
					<span></span><span></span><span></span>
				</button>
				<a href="/" class="prv-nav__logo">
					<img src="/logo@2x.png" alt="RaceRead" class="prv-nav__logo-img" />
				</a>
			</div>
			<button class="prv-nav__lang" onclick={() => locale.set($locale === 'en' ? 'tr' : 'en')}>
				{$locale === 'en' ? 'TR' : 'EN'}
			</button>
		</div>
	</nav>

	<div class="prv-layout">

		<!-- SIDEBAR -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<aside class="prv-sidebar" class:collapsed={sidebarCollapsed} class:prv-sidebar--open={sidebarOpen}
			
			>

			<!-- Toggle button -->
			<button class="prv-sidebar__toggle" onclick={() => sidebarCollapsed = !sidebarCollapsed} title={sidebarCollapsed ? 'Expand' : 'Collapse'}>
				<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
					<path d={sidebarCollapsed ? 'M6 3l5 5-5 5' : 'M10 3L5 8l5 5'} stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
				</svg>
			</button>

			<div class="prv-sidebar__content">
				<!-- Season -->
				<div class="prv-sidebar__section">
					<h2 class="prv-sidebar__heading">{$t('home.sidebar_season')}</h2>
					<p class="prv-sidebar__version">{$t('home.round')} {races.length}{calendar.length ? ' / ' + calendar.length : ''}</p>
				</div>

				<!-- Races -->
				<div class="prv-sidebar__section">
					<p class="prv-sidebar__label">{$t('home.sidebar_races')}</p>
					<nav class="prv-sidebar__nav">
						{#each races as race, i}
							<a href="/race/{race.id}" class="prv-sidebar__race" onclick={() => sidebarOpen = false}>
								<span class="prv-sidebar__race-code">R{String(i + 1).padStart(2, '0')}</span>
								<span class="prv-sidebar__race-name">{race.circuit}</span>
								<span class="prv-sidebar__race-winner" style="color:{getTeamColor(race.winner)}">{race.winner}</span>
							</a>
						{/each}
						{#each calendar.filter(c => !isCompleted(c)).slice(0, 2) as next}
							<div class="prv-sidebar__race prv-sidebar__race--upcoming">
								<span class="prv-sidebar__race-code">R{String(next.round).padStart(2, '0')}</span>
								<span class="prv-sidebar__race-name">{next.code}</span>
								<span class="prv-sidebar__race-date">{formatDateShort(next.date)}</span>
							</div>
						{/each}
					</nav>
				</div>

				<!-- Standings + About links -->
				<div class="prv-sidebar__section prv-sidebar__section--last">
					<a href="/standings" class="prv-sidebar__about-link">
						<span>{$t('nav.standings')}</span>
						<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
					</a>
					<a href="/about" class="prv-sidebar__about-link">
						<span>{$t('home.sidebar_about')}</span>
						<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
					</a>
				</div>

				<!-- Status -->
				<div class="prv-sidebar__bottom">
					<div class="prv-sidebar__status">
						<div class="prv-sidebar__dot"></div>
						<div>
							<p class="prv-sidebar__status-label">{$t('home.sidebar_status')}</p>
							<p class="prv-sidebar__status-value">{$t('home.sidebar_active')}</p>
						</div>
					</div>
				</div>
			</div>

			<!-- Collapsed: mini race indicators -->
			<div class="prv-sidebar__mini">
				{#each races as race, i}
					<a href="/race/{race.id}" class="prv-sidebar__mini-race" title="{race.name}" style="border-left-color:{getTeamColor(race.winner)}">
						<span>R{i + 1}</span>
					</a>
				{/each}
				<div class="prv-sidebar__mini-dot">
					<div class="prv-sidebar__dot"></div>
				</div>
			</div>

		</aside>

		{#if sidebarOpen}
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div class="prv-overlay" onclick={() => sidebarOpen = false}></div>
		{/if}

		<!-- MAIN -->
		<div class="prv-main">

			<section class="prv-hero">
				
			<!-- Dynamic circuit with racing drivers -->
			{#if trackPath}
			<svg class="prv-hero__circuit" viewBox="0 0 500 460" preserveAspectRatio="xMidYMid meet">
				<defs><path id="race-track" d={trackPath} /></defs>
				<use href="#race-track" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
				<!-- 11 teams, 2 drivers each = 22 dots (front runners bigger) -->
				<!-- Mercedes -->
				<circle r="5" fill="#00D7B6" opacity="0.85"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="17.8s" repeatCount="indefinite" begin="0s"><mpath href="#race-track" /></animateMotion></circle>
				<circle r="4" fill="#00D7B6" opacity="0.6"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="18.1s" repeatCount="indefinite" begin="-3s"><mpath href="#race-track" /></animateMotion></circle>
				<!-- Ferrari -->
				<circle r="5" fill="#ED1131" opacity="0.85"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="17.9s" repeatCount="indefinite" begin="-5s"><mpath href="#race-track" /></animateMotion></circle>
				<circle r="4" fill="#ED1131" opacity="0.6"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="18.3s" repeatCount="indefinite" begin="-8s"><mpath href="#race-track" /></animateMotion></circle>
				<!-- Red Bull -->
				<circle r="5" fill="#4781D7" opacity="0.85"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="18s" repeatCount="indefinite" begin="-1.5s"><mpath href="#race-track" /></animateMotion></circle>
				<circle r="4" fill="#4781D7" opacity="0.55"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="18.6s" repeatCount="indefinite" begin="-10s"><mpath href="#race-track" /></animateMotion></circle>
				<!-- McLaren -->
				<circle r="5" fill="#F47600" opacity="0.85"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="18s" repeatCount="indefinite" begin="-6.5s"><mpath href="#race-track" /></animateMotion></circle>
				<circle r="4" fill="#F47600" opacity="0.6"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="18.4s" repeatCount="indefinite" begin="-13s"><mpath href="#race-track" /></animateMotion></circle>
				<!-- Aston Martin -->
				<circle r="4" fill="#229971" opacity="0.6"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="18.5s" repeatCount="indefinite" begin="-7s"><mpath href="#race-track" /></animateMotion></circle>
				<circle r="3.5" fill="#229971" opacity="0.45"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="18.9s" repeatCount="indefinite" begin="-14s"><mpath href="#race-track" /></animateMotion></circle>
				<!-- Alpine -->
				<circle r="4" fill="#00A1E8" opacity="0.6"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="18.6s" repeatCount="indefinite" begin="-4s"><mpath href="#race-track" /></animateMotion></circle>
				<circle r="3.5" fill="#00A1E8" opacity="0.45"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="19s" repeatCount="indefinite" begin="-11s"><mpath href="#race-track" /></animateMotion></circle>
				<!-- Williams -->
				<circle r="4" fill="#1868DB" opacity="0.55"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="18.7s" repeatCount="indefinite" begin="-9s"><mpath href="#race-track" /></animateMotion></circle>
				<circle r="3.5" fill="#1868DB" opacity="0.4"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="19.1s" repeatCount="indefinite" begin="-16s"><mpath href="#race-track" /></animateMotion></circle>
				<!-- Racing Bulls -->
				<circle r="3.5" fill="#6C98FF" opacity="0.5"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="18.8s" repeatCount="indefinite" begin="-2.5s"><mpath href="#race-track" /></animateMotion></circle>
				<circle r="3" fill="#6C98FF" opacity="0.4"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="19.2s" repeatCount="indefinite" begin="-12s"><mpath href="#race-track" /></animateMotion></circle>
				<!-- Haas -->
				<circle r="3.5" fill="#9C9FA2" opacity="0.5"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="18.9s" repeatCount="indefinite" begin="-15s"><mpath href="#race-track" /></animateMotion></circle>
				<circle r="3" fill="#9C9FA2" opacity="0.35"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="19.3s" repeatCount="indefinite" begin="-7.5s"><mpath href="#race-track" /></animateMotion></circle>
				<!-- Audi -->
				<circle r="3.5" fill="#F50537" opacity="0.5"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="19s" repeatCount="indefinite" begin="-4.5s"><mpath href="#race-track" /></animateMotion></circle>
				<circle r="3" fill="#F50537" opacity="0.35"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="19.4s" repeatCount="indefinite" begin="-14.5s"><mpath href="#race-track" /></animateMotion></circle>
				<!-- Cadillac -->
				<circle r="3.5" fill="#909090" opacity="0.45"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="19.1s" repeatCount="indefinite" begin="-11.5s"><mpath href="#race-track" /></animateMotion></circle>
				<circle r="3" fill="#909090" opacity="0.3"><animateMotion keyPoints="1;0" keyTimes="0;1" calcMode="linear" dur="19.5s" repeatCount="indefinite" begin="-17s"><mpath href="#race-track" /></animateMotion></circle>
			</svg>
			{/if}
				<div class="prv-hero__content">
					<span class="prv-hero__tagline">{$t('home.tagline')}</span>
					<h1 class="prv-hero__title">
						{$t('home.headline_1')}<br />
						<span class="prv-hero__title--accent">{$t('home.headline_2')}</span>
					</h1>
					<p class="prv-hero__desc">{$t('home.desc')}</p>
					<div class="prv-hero__actions">
						<a href="#races" class="prv-btn prv-btn--primary">{$t('home.cta_analyze')}</a>
						<a href="/guide" class="prv-btn prv-btn--ghost">{$t('home.cta_docs')}</a>
					</div>
				</div>
			</section>

			{#if calendar.length > 1}
			<section class="prv-timeline">
				<div class="prv-timeline__header">
					<h2 class="prv-timeline__title">{$t('home.season_title')}</h2>
					<p class="prv-timeline__sub">{$t('home.round')} {races.length} / {calendar.length}</p>
				</div>
				<div class="prv-timeline__track">
					<div class="prv-timeline__line"></div>
					<div class="prv-timeline__progress" style="width: {races.length ? ((races.length - 1) / (calendar.length - 1)) * 100 : 0}%"></div>
					<div class="prv-timeline__points">
						{#each calendar as cal}
							{@const done = isCompleted(cal)}
							{@const raceId = getRaceId(cal)}
							{#if done && raceId}
								<a href="/race/{raceId}" class="prv-timeline__point prv-timeline__point--done" title={cal.name}>
									<div class="prv-timeline__diamond"></div>
									<span class="prv-timeline__code">{cal.code}</span>
								</a>
							{:else}
								<div class="prv-timeline__point prv-timeline__point--future" title={cal.name}>
									<div class="prv-timeline__diamond"></div>
									<span class="prv-timeline__code">{cal.code}</span>
								</div>
							{/if}
						{/each}
					</div>
				</div>
			</section>
			{/if}

			<section class="prv-races" id="races">
				<div class="prv-races__grid">
					{#each races as race, i}
						{@const extras = computeExtras(race)}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<a href="/race/{race.id}" class="prv-card"
							onmouseenter={() => hoveredCard = race.id}
							onmouseleave={() => hoveredCard = null}>
							<div class="prv-card__top">
								<p class="prv-card__round">R{String(i + 1).padStart(2, '0')} / {formatDate(race.date)}</p>
								<h3 class="prv-card__name">{raceName(race.name)}</h3>
							</div>
							<div class="prv-card__info">
								<div class="prv-card__winner">
									<div class="prv-card__team-bar" style="background:{getTeamColor(race.winner)}"></div>
									<span class="prv-card__winner-text">{$t('home.winner')}: {DRIVER_NAMES[race.winner] || race.winner}</span>
								</div>
								<div class="prv-card__meta">
									<span>{race.total_laps} {$t('home.laps_label')}</span>
									{#if extras.temp}<span>{extras.temp + '\u00B0C'}</span>{/if}
									<span>{extras.rainfall === false ? 'DRY' : extras.rainfall ? 'WET' : ''}</span>
								</div>
							</div>
							<div class="prv-card__overlay" class:prv-card__overlay--visible={hoveredCard === race.id}>
								<div class="prv-card__stats">
									{#if extras.fastest}
										<div class="prv-card__stat">
											<span class="prv-card__stat-label">{$t('home.fastest_lap')}</span>
											<span class="prv-card__stat-value">{extras.fastest} <span class="prv-card__stat-sub">({extras.fastestDriver})</span></span>
										</div>
									{/if}
									{#if extras.sc}
										<div class="prv-card__stat">
											<span class="prv-card__stat-label">{$t('home.safety_cars')}</span>
											<span class="prv-card__stat-value">{extras.sc}</span>
										</div>
									{/if}
								</div>
								<div class="prv-card__cta">{$t('home.analyze')} <span class="prv-card__arrow">&rarr;</span></div>
							</div>
						</a>
					{/each}
					{#each calendar.filter(c => !isCompleted(c)).slice(0, 1) as next}
						<div class="prv-card prv-card--upcoming">
							<div class="prv-card__top prv-card__top--upcoming">
								<div>
									<p class="prv-card__round prv-card__round--muted">{$t('home.upcoming')} / {formatDate(next.date)}</p>
									<h3 class="prv-card__name prv-card__name--dim">{calName(next)}</h3>
								</div>
								<TrackSilhouette code={next.code} size={64} opacity={0.45} />
							</div>
							<div class="prv-card__pending">{$t('home.no_data')}</div>
						</div>
					{/each}
				</div>
			</section>

			<a href="/guide" class="prv-guide">
				<div class="prv-guide__txt">
					<span class="prv-guide__k">{$t('home.guide_k')}</span>
					<span class="prv-guide__t">{$t('home.guide_t')}</span>
				</div>
				<span class="prv-guide__arrow">&rarr;</span>
			</a>

			{#if classics.length}
			<section class="prv-classics">
				<div class="prv-timeline__header">
					<h2 class="prv-timeline__title">{$t('home.classics_title')}</h2>
					<p class="prv-timeline__sub">{$t('home.classics_sub')}</p>
				</div>
				<div class="prv-classics__grid">
					{#each classics as c (c.id)}
						<a href="/race/{c.id}" class="prv-classic">
							<div class="prv-classic__top">
								<span class="prv-classic__year">{c.year}</span>
								<span class="prv-classic__spice">SPICE {c.spice}</span>
							</div>
							<div class="prv-classic__mid">
								<h3 class="prv-classic__name">{raceName(c.name)}</h3>
								<TrackSilhouette code={c.code} size={52} opacity={0.45} />
							</div>
							<div class="prv-classic__meta">
								<span class="prv-card__team-bar" style="background:{TEAM_COLORS[c.winner_team] || '#888'}"></span>
								<span class="prv-classic__winner">{c.winner}</span>
								{#each c.tags || [] as tag}<span class="prv-classic__tag">{tag}</span>{/each}
							</div>
						</a>
					{/each}
				</div>
			</section>
			{/if}

			<footer class="prv-footer">
				<div class="prv-footer__row">
					<span class="prv-footer__copy">{$t('home.footer_copy')}</span>
					<div class="prv-footer__links">
						<span>{$t('home.footer_data')}</span>
						<a href="https://github.com/jolpica/jolpica-f1" target="_blank" rel="noopener noreferrer" class="prv-footer__link">{$t('footer.jolpica')}</a>
						<span>{$t('home.footer_energy')}</span>
					</div>
				</div>
				<p class="prv-footer__legal">{$t('footer.disclaimer')}</p>
			</footer>
		</div>
	</div>
</div>

<style>
	.prv {
		--p-bg: #0F1117; --p-bg2: #1A1D27; --p-bgc: #22252F;
		--p-t: #E8E8ED; --p-t2: #9CA3AF; --p-tm: #7D8794;
		--p-brd: #2E3240; --p-ac: #E24B4A; --p-ach: #C93B3A;
		--p-ac2: #F07B7A; /* accent for small text - passes WCAG AA on dark bg */
		--p-fh: 'Space Grotesk', sans-serif;
		--p-fb: 'DM Sans', 'Inter', sans-serif;
		--p-fm: 'JetBrains Mono', monospace;
		--sb-w: 240px; --sb-cw: 48px;
		position: fixed; inset: 0; z-index: 200;
		overflow: hidden; background: var(--p-bg);
		color: var(--p-t); font-family: var(--p-fb);
		-webkit-font-smoothing: antialiased;
	}

	/* ── NAV ── */
	.prv-nav { position: relative; z-index: 60; background: var(--p-bg); border-bottom: 1px solid rgba(46,50,64,.6); }
	.prv-nav__inner { padding: 0 1.25rem; height: 56px; display: flex; align-items: center; justify-content: space-between; }
	.prv-nav__left { display: flex; align-items: center; gap: 1rem; }
	.prv-nav__logo { display: flex; align-items: center; text-decoration: none; }
	.prv-nav__logo:hover { text-decoration: none; }
	.prv-nav__logo-img { height: 44px; width: auto; }
	.prv-nav__burger { display: none; flex-direction: column; gap: 4px; background: none; border: none; cursor: pointer; padding: 4px; }
	.prv-nav__burger span { display: block; width: 18px; height: 2px; background: var(--p-t2); }
	.prv-nav__lang { font-family: var(--p-fm); font-size: 10px; font-weight: 700; letter-spacing: .1em; color: var(--p-ac); background: none; border: 1px solid var(--p-brd); padding: 5px 12px; cursor: pointer; }
	.prv-nav__lang:hover { background: var(--p-bg2); }

	/* ── LAYOUT ── */
	.prv-layout { display: flex; height: calc(100vh - 56px); }

	/* ── SIDEBAR ── */
	.prv-sidebar {
		width: var(--sb-w); min-width: var(--sb-w);
		background: var(--p-bg2);
		border-right: 1px solid rgba(46,50,64,.5);
		display: flex; flex-direction: column;
		position: relative; z-index: 55;
		transition: width .3s cubic-bezier(.4,0,.2,1), min-width .3s cubic-bezier(.4,0,.2,1);
		overflow: hidden;
	}
	.prv-sidebar.collapsed { width: var(--sb-cw); min-width: var(--sb-cw); }

	/* Toggle button */
	.prv-sidebar__toggle {
		position: absolute; top: 12px; right: 8px; z-index: 5;
		width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
		background: var(--p-bg2); border: 1px solid rgba(46,50,64,.5);
		color: var(--p-tm); cursor: pointer; transition: color .15s, background .15s;
	}
	.prv-sidebar__toggle:hover { color: var(--p-t); background: var(--p-bgc); }
	.collapsed .prv-sidebar__toggle { right: auto; left: 50%; transform: translateX(-50%); }

	/* Expanded content */
	.prv-sidebar__content {
		display: flex; flex-direction: column; flex: 1;
		overflow-y: auto; overflow-x: hidden; white-space: nowrap;
		opacity: 1; transition: opacity .2s ease .1s;
		position: relative; z-index: 2;
	}
	.collapsed .prv-sidebar__content { opacity: 0; pointer-events: none; transition: opacity .15s ease 0s; }

	/* Mini collapsed view */
	.prv-sidebar__mini {
		display: flex; flex-direction: column; align-items: center;
		gap: 6px; padding-top: 48px;
		opacity: 0; pointer-events: none;
		transition: opacity .15s ease 0s;
		position: absolute; top: 0; left: 0; right: 0; bottom: 0;
	}
	.collapsed .prv-sidebar__mini { opacity: 1; pointer-events: auto; transition: opacity .2s ease .15s; }
	.prv-sidebar__mini-race {
		font-family: var(--p-fm); font-size: 9px; font-weight: 700;
		color: var(--p-t2); text-decoration: none;
		padding: 4px 0; border-left: 2px solid transparent;
		padding-left: 6px; width: 36px; text-align: center;
		transition: color .15s;
	}
	.prv-sidebar__mini-race:hover { color: var(--p-ac); text-decoration: none; }
	.prv-sidebar__mini-dot { margin-top: auto; margin-bottom: 16px; }

	/* Sidebar sections */
	.prv-sidebar__section { padding: 1.25rem; border-bottom: 1px solid rgba(46,50,64,.4); }
	.prv-sidebar__section--last { border-bottom: none; }
	.prv-sidebar__heading { font-family: var(--p-fh); font-weight: 700; font-size: 14px; text-transform: uppercase; }
	.prv-sidebar__version { font-family: var(--p-fm); font-size: 10px; color: var(--p-ac2); letter-spacing: .08em; text-transform: uppercase; margin-top: 3px; }
	.prv-sidebar__label { font-family: var(--p-fm); font-size: 9px; color: var(--p-tm); text-transform: uppercase; letter-spacing: .1em; margin-bottom: .5rem; }
	.prv-sidebar__nav { display: flex; flex-direction: column; gap: 1px; }
	.prv-sidebar__race { display: flex; align-items: center; gap: .5rem; padding: .45rem .5rem; text-decoration: none; color: inherit; margin: 0 -.25rem; transition: background .15s; }
	a.prv-sidebar__race:hover { background: rgba(226,75,74,.08); text-decoration: none; }
	.prv-sidebar__race--upcoming { opacity: .35; }
	.prv-sidebar__race-code { font-family: var(--p-fm); font-size: 10px; color: var(--p-ac); min-width: 24px; }
	.prv-sidebar__race-name { font-family: var(--p-fm); font-size: 11px; flex: 1; }
	.prv-sidebar__race-winner { font-family: var(--p-fm); font-size: 10px; font-weight: 700; }
	.prv-sidebar__race-date { font-family: var(--p-fm); font-size: 9px; color: var(--p-tm); }
	.prv-sidebar__about-text { font-size: 12px; line-height: 1.6; color: var(--p-t2); }
	.prv-sidebar__bottom { margin-top: auto; padding: 1.25rem; background: rgba(15,17,23,.5); }
	.prv-sidebar__status { display: flex; align-items: center; gap: .6rem; }
	.prv-sidebar__dot { width: 7px; height: 7px; background: #22C55E; border-radius: 50%; flex-shrink: 0; }
	.prv-sidebar__status-label { font-family: var(--p-fm); font-size: 9px; color: var(--p-tm); text-transform: uppercase; letter-spacing: .05em; }
	.prv-sidebar__status-value { font-family: var(--p-fm); font-size: 10px; color: #22C55E; }

	/* ── MAIN ── */
	.prv-main { flex: 1; overflow-y: auto; overflow-x: hidden; }

	/* ── HERO ── */
	.prv-hero { position: relative; padding: 4rem 3rem; overflow: hidden; }
	.prv-hero__circuit { position: absolute; top: 45%; right: -8%; transform: translateY(-50%); width: 65%; max-width: 800px; color: rgba(226,75,74,.15); pointer-events: none; filter: drop-shadow(0 0 24px rgba(226,75,74,.1)); }
	.prv-hero__content { position: relative; z-index: 1; max-width: 680px; }
	.prv-hero__tagline { display: block; font-family: var(--p-fm); font-size: 11px; letter-spacing: .2em; text-transform: uppercase; color: var(--p-ac); margin-bottom: 1.25rem; }
	.prv-hero__title { font-family: var(--p-fh); font-weight: 700; font-size: clamp(30px,4.5vw,56px); line-height: 1.05; letter-spacing: -.03em; text-transform: uppercase; margin-bottom: 1.25rem; }
	.prv-hero__title--accent { color: var(--p-ac); }
	.prv-hero__desc { font-size: 15px; line-height: 1.7; color: var(--p-t2); max-width: 520px; margin-bottom: 2rem; }
	.prv-hero__actions { display: flex; flex-wrap: wrap; gap: 1rem; }

	/* ── BUTTONS ── */
	.prv-btn { font-family: var(--p-fh); font-weight: 600; font-size: 12px; letter-spacing: .06em; text-transform: uppercase; padding: 13px 28px; text-decoration: none; transition: all .15s; cursor: pointer; border: none; }
	.prv-btn:hover { text-decoration: none; }
	.prv-btn--primary { background: var(--p-ach); color: #fff; }
	.prv-btn--primary:hover { background: #B23231; }
	.prv-btn--ghost { background: none; border: 1px solid var(--p-brd); color: var(--p-t); }
	.prv-btn--ghost:hover { background: var(--p-bg2); }

	/* ── TIMELINE ── */
	.prv-timeline { background: var(--p-bg2); padding: 2.5rem 3rem; }
	.prv-timeline__header { margin-bottom: 1.5rem; }
	.prv-timeline__title { font-family: var(--p-fh); font-weight: 700; font-size: 22px; text-transform: uppercase; }
	.prv-timeline__sub { font-family: var(--p-fm); font-size: 11px; color: var(--p-ac2); letter-spacing: .12em; text-transform: uppercase; margin-top: 3px; }
	.prv-timeline__track { position: relative; height: 70px; display: flex; align-items: center; }
	.prv-timeline__line { position: absolute; width: 100%; height: 2px; background: var(--p-brd); top: 50%; transform: translateY(-50%); }
	.prv-timeline__progress { position: absolute; height: 2px; background: var(--p-ac); top: 50%; transform: translateY(-50%); left: 0; }
	.prv-timeline__points { position: relative; width: 100%; display: flex; justify-content: space-between; align-items: center; }
	.prv-timeline__point { display: flex; flex-direction: column; align-items: center; gap: 6px; text-decoration: none; color: inherit; cursor: default; }
	a.prv-timeline__point { cursor: pointer; }
	a.prv-timeline__point:hover { text-decoration: none; }
	a.prv-timeline__point:hover .prv-timeline__diamond { transform: rotate(45deg) scale(1.3); }
	.prv-timeline__diamond { width: 13px; height: 13px; transform: rotate(45deg); transition: transform .15s; }
	.prv-timeline__point--done .prv-timeline__diamond { background: var(--p-ac); }
	.prv-timeline__point--future .prv-timeline__diamond { border: 1px solid var(--p-tm); width: 7px; height: 7px; }
	.prv-timeline__point--future { opacity: .3; }
	.prv-timeline__code { font-family: var(--p-fm); font-size: 11px; text-transform: uppercase; color: var(--p-tm); }
	.prv-timeline__point--done .prv-timeline__code { color: var(--p-t); font-weight: 700; }

	/* ── CARDS ── */
	.prv-races { padding: 2.5rem 3rem; }
	.prv-races__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 2px; }
	.prv-card { position: relative; overflow: hidden; background: var(--p-bg2); padding: 1.5rem; display: flex; flex-direction: column; min-height: 196px; text-decoration: none; color: inherit; transition: background .2s, border-color .2s; border: 1px solid transparent; }
	.prv-card:hover { background: var(--p-bgc); border-color: rgba(226,75,74,.2); text-decoration: none; }
	.prv-card--upcoming { background: var(--p-bg); border: 1px solid var(--p-brd); }
	.prv-card__top--upcoming { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
	.prv-card__top { margin-bottom: 1.25rem; }
	.prv-card__round { font-family: var(--p-fm); font-size: 10px; color: var(--p-ac2); }
	.prv-card__round--muted { color: var(--p-tm); }
	.prv-card__name { font-family: var(--p-fh); font-weight: 700; font-size: 18px; text-transform: uppercase; line-height: 1.2; margin-top: 5px; }
	.prv-card__name--dim { opacity: .35; }
	.prv-card__info { margin-top: auto; }
	.prv-card__winner { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
	.prv-card__team-bar { width: 3px; height: 16px; flex-shrink: 0; }
	.prv-card__winner-text { font-family: var(--p-fm); font-size: 11px; text-transform: uppercase; }
	.prv-card__meta { display: flex; gap: 1rem; font-family: var(--p-fm); font-size: 10px; color: var(--p-tm); text-transform: uppercase; }
	.prv-card__pending { margin-top: auto; font-family: var(--p-fm); font-size: 10px; color: var(--p-tm); text-transform: uppercase; letter-spacing: .1em; opacity: .4; }
	.prv-card__overlay { position: absolute; inset: auto 0 0 0; background: var(--p-bgc); padding: .85rem 1.5rem .9rem; transform: translateY(100%); transition: transform .25s ease; border-top: 1px solid rgba(226,75,74,.15); }
	.prv-card__overlay--visible { transform: translateY(0); }
	.prv-card__stats { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; margin-bottom: .5rem; }
	.prv-card__stat-label { display: block; font-family: var(--p-fm); font-size: 9px; color: var(--p-ac2); text-transform: uppercase; margin-bottom: 2px; }
	.prv-card__stat-value { font-family: var(--p-fm); font-size: 12px; font-weight: 700; }
	.prv-card__stat-sub { font-size: 9px; opacity: .5; }
	.prv-card__cta { display: flex; align-items: center; justify-content: flex-end; gap: 6px; font-family: var(--p-fh); font-weight: 700; font-size: 10px; color: var(--p-ac); text-transform: uppercase; letter-spacing: .08em; }
	.prv-card__arrow { transition: transform .15s; }
	.prv-card:hover .prv-card__arrow { transform: translateX(3px); }

	/* ── CLASSICS SHELF ── */
	.prv-classics { padding: 2.5rem 3rem; background: linear-gradient(180deg, var(--p-bg) 0%, #12141c 100%); border-top: 1px solid rgba(46,50,64,.5); }
	.prv-classics__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 2px; margin-top: 1.25rem; }
	.prv-classic { background: var(--p-bg2); padding: 1.1rem 1.25rem; display: flex; flex-direction: column; gap: 6px; text-decoration: none; color: inherit; border: 1px solid transparent; transition: background .2s, border-color .2s; }
	.prv-classic:hover { background: var(--p-bgc); border-color: rgba(245,158,11,.35); text-decoration: none; }
	.prv-classic__top { display: flex; justify-content: space-between; align-items: baseline; }
	.prv-classic__year { font-family: var(--p-fm); font-size: 10px; color: var(--p-t2); letter-spacing: .1em; }
	.prv-classic__spice { font-family: var(--p-fm); font-size: 10px; font-weight: 700; color: #F59E0B; letter-spacing: .06em; }
	.prv-classic__mid { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
	.prv-classic__name { font-family: var(--p-fh); font-weight: 700; font-size: 15px; text-transform: uppercase; line-height: 1.25; }
	.prv-classic__meta { margin-top: auto; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
	.prv-classic__winner { font-family: var(--p-fm); font-size: 11px; font-weight: 700; }
	.prv-classic__tag { font-family: var(--p-fm); font-size: 8.5px; letter-spacing: .06em; border: 1px solid var(--p-brd); color: var(--p-t2); padding: 1px 6px; text-transform: uppercase; }
	@media (max-width: 900px) { .prv-classics { padding: 2rem 1.5rem; } }

	/* ── FOOTER ── */
	.prv-sidebar__about-link {
		display: flex; align-items: center; justify-content: space-between;
		font-family: var(--p-fm); font-size: 11px; color: var(--p-t2);
		text-decoration: none; text-transform: uppercase; letter-spacing: .08em;
		padding: .4rem 0; transition: color .15s;
	}
	.prv-sidebar__about-link:hover { color: var(--p-ac); text-decoration: none; }

	.prv-footer { background: #0A0C12; padding: 1.5rem 3rem; border-top: 1px solid rgba(46,50,64,.5); }
	.prv-footer__row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: .5rem; }
	.prv-footer__link { color: inherit; text-decoration: none; }
	.prv-footer__link:hover { color: var(--p-t2); text-decoration: none; }
	.prv-footer__legal { margin-top: .7rem; font-family: var(--p-fm); font-size: 9px; line-height: 1.6; color: var(--p-tm); opacity: .55; text-transform: none; letter-spacing: .02em; }
	.prv-footer__copy { font-family: var(--p-fm); font-size: 10px; opacity: .35; text-transform: uppercase; letter-spacing: .12em; }
	.prv-footer__links { display: flex; gap: 2rem; font-family: var(--p-fm); font-size: 10px; text-transform: uppercase; letter-spacing: .08em; opacity: .25; }

	/* ── MOBILE ── */
	.prv-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.6); z-index: 54; }
	@media (max-width: 900px) {
		.prv-sidebar { position: fixed; top: 56px; left: 0; bottom: 0; width: var(--sb-w); min-width: var(--sb-w); transform: translateX(-100%); transition: transform .25s ease; }
		.prv-sidebar--open { transform: translateX(0); }
		.prv-sidebar.collapsed { width: var(--sb-w); min-width: var(--sb-w); } /* no collapse on mobile */
		.collapsed .prv-sidebar__content { opacity: 1; pointer-events: auto; position: static; }
		.collapsed .prv-sidebar__mini { display: none; }
		.prv-sidebar__toggle { display: none; }
		.prv-overlay { display: block; }
		.prv-nav__burger { display: flex; }
		.prv-hero, .prv-timeline, .prv-races { padding-left: 1.5rem; padding-right: 1.5rem; }
		.prv-races__grid { grid-template-columns: 1fr; }
		.prv-sidebar__about-link {
		display: flex; align-items: center; justify-content: space-between;
		font-family: var(--p-fm); font-size: 11px; color: var(--p-t2);
		text-decoration: none; text-transform: uppercase; letter-spacing: .08em;
		padding: .4rem 0; transition: color .15s;
	}
	.prv-sidebar__about-link:hover { color: var(--p-ac); text-decoration: none; }

	.prv-footer { flex-direction: column; gap: .75rem; text-align: center; padding: 1.5rem; }
	}
	@media (max-width: 480px) {
		.prv-hero__title { font-size: 26px; }
		.prv-btn { padding: 11px 18px; font-size: 11px; }
		.prv-hero, .prv-timeline, .prv-races { padding-left: 1rem; padding-right: 1rem; }
	}

	.prv-guide {
		display: flex; align-items: center; justify-content: space-between; gap: 16px;
		margin: 28px 0 4px; padding: 16px 20px;
		background: var(--bg-secondary, #1A1D27); border: 1px solid var(--border, #2E3240);
		border-left: 3px solid var(--accent, #E24B4A); text-decoration: none;
		transition: border-color .15s, background .15s;
	}
	.prv-guide:hover { border-color: #6B7280; border-left-color: var(--accent, #E24B4A); background: #1E2230; text-decoration: none; }
	.prv-guide:hover .prv-guide__arrow { transform: translateX(4px); }
	.prv-guide__k { display: block; font-family: var(--font-mono); font-size: 9px; letter-spacing: .14em; color: var(--accent, #E24B4A); text-transform: uppercase; margin-bottom: 3px; }
	.prv-guide__t { font-family: var(--font-heading); font-size: 15px; font-weight: 600; color: var(--text-primary, #E8E8ED); letter-spacing: -.01em; }
	.prv-guide__arrow { font-size: 18px; color: var(--text-muted, #7D8794); transition: transform .15s; }
</style>
