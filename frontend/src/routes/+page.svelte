<script>
	import { locale } from '$lib/i18n/index.js';
	import { TEAM_COLORS } from '$lib/constants.js';

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

	const L = {
		en: {
			tagline: 'Engineered Intelligence',
			headline_1: 'Post-Race Intelligence',
			headline_2: 'for F1 Telemetry.',
			desc: 'AI-powered energy inference and telemetry analysis for every Grand Prix.',
			cta_analyze: 'Explore Races',
			cta_docs: 'How It Works',
			season_title: '2026 Season Progression',
			winner: 'Winner',
			laps_label: 'Laps',
			analyze: 'Analyze',
			upcoming: 'Upcoming',
			round: 'Round',
			no_data: 'Data pending',
			fastest_lap: 'Fastest Lap',
			safety_cars: 'Safety Cars',
			footer_copy: '\u00A9 2026 RaceRead \u2022 F1 Post-Race Telemetry Analysis',
			footer_data: 'Data: FastF1',
			footer_energy: 'Energy: Inferred',
			sidebar_season: '2026 Season',
			sidebar_about: 'About',
			sidebar_about_text: 'Post-race telemetry analysis with AI energy inference. Built for the serious paddock analyst.',
			sidebar_races: 'Completed Races',
			sidebar_status: 'System Status',
			sidebar_active: 'Active Feed',
		},
		tr: {
			tagline: 'M\u00FChendislik Zekas\u0131',
			headline_1: 'Yar\u0131\u015F Sonras\u0131 \u0130stihbarat',
			headline_2: 'F1 Telemetrisi i\u00E7in.',
			desc: 'Her Grand Prix i\u00E7in AI destekli enerji \u00E7\u0131kar\u0131m\u0131 ve telemetri analizi.',
			cta_analyze: 'Yar\u0131\u015Flar\u0131 \u0130ncele',
			cta_docs: 'Nas\u0131l \u00C7al\u0131\u015F\u0131r',
			season_title: '2026 Sezon \u0130lerlemesi',
			winner: 'Kazanan',
			laps_label: 'Tur',
			analyze: 'Analiz Et',
			upcoming: 'Yak\u0131nda',
			round: 'Yar\u0131\u015F',
			no_data: 'Veri bekleniyor',
			fastest_lap: 'En H\u0131zl\u0131 Tur',
			safety_cars: 'G\u00FCvenlik Arac\u0131',
			footer_copy: '\u00A9 2026 RaceRead \u2022 F1 Yar\u0131\u015F Sonras\u0131 Telemetri Analizi',
			footer_data: 'Veri: FastF1',
			footer_energy: 'Enerji: \u00C7\u0131kar\u0131msal',
			sidebar_season: '2026 Sezonu',
			sidebar_about: 'Hakk\u0131nda',
			sidebar_about_text: 'AI enerji \u00E7\u0131kar\u0131m\u0131 ile yar\u0131\u015F sonras\u0131 telemetri analizi. Ciddi padok analistleri i\u00E7in tasarland\u0131.',
			sidebar_races: 'Tamamlanan Yar\u0131\u015Flar',
			sidebar_status: 'Sistem Durumu',
			sidebar_active: 'Aktif Besleme',
		}
	};
	let tr = $derived(L[$locale] || L.en);

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

	const CALENDAR_2026 = [
		{ code: 'AUS', name: 'Australian GP', date: '2026-03-08', round: 1 },
		{ code: 'CHN', name: 'Chinese GP', date: '2026-03-15', round: 2 },
		{ code: 'JPN', name: 'Japanese GP', date: '2026-03-29', round: 3 },
		{ code: 'MIA', name: 'Miami GP', date: '2026-05-03', round: 4 },
		{ code: 'EMI', name: 'Emilia Romagna GP', date: '2026-05-17', round: 5 },
		{ code: 'MON', name: 'Monaco GP', date: '2026-05-24', round: 6 },
		{ code: 'ESP', name: 'Spanish GP', date: '2026-06-07', round: 7 },
		{ code: 'CAN', name: 'Canadian GP', date: '2026-06-14', round: 8 },
		{ code: 'AUT', name: 'Austrian GP', date: '2026-06-28', round: 9 },
		{ code: 'GBR', name: 'British GP', date: '2026-07-05', round: 10 },
		{ code: 'BEL', name: 'Belgian GP', date: '2026-07-26', round: 11 },
		{ code: 'HUN', name: 'Hungarian GP', date: '2026-08-02', round: 12 },
		{ code: 'NED', name: 'Dutch GP', date: '2026-08-30', round: 13 },
		{ code: 'ITA', name: 'Italian GP', date: '2026-09-06', round: 14 },
		{ code: 'AZE', name: 'Azerbaijan GP', date: '2026-09-20', round: 15 },
		{ code: 'SGP', name: 'Singapore GP', date: '2026-10-04', round: 16 },
		{ code: 'USA', name: 'US GP', date: '2026-10-18', round: 17 },
		{ code: 'MEX', name: 'Mexican GP', date: '2026-10-25', round: 18 },
		{ code: 'BRA', name: 'Brazilian GP', date: '2026-11-08', round: 19 },
		{ code: 'QAT', name: 'Qatar GP', date: '2026-11-29', round: 20 },
		{ code: 'ABU', name: 'Abu Dhabi GP', date: '2026-12-06', round: 21 },
	];


	const RACE_NAMES_TR = {
		'Australian Grand Prix': 'Avustralya Grand Prix',
		'Chinese Grand Prix': '\u00C7in Grand Prix',
		'Japanese Grand Prix': 'Japonya Grand Prix',
		'Miami Grand Prix': 'Miami Grand Prix',
	};
	function raceName(name) {
		const n = ($locale === 'tr' && RACE_NAMES_TR[name]) ? RACE_NAMES_TR[name] : name;
		// Uppercase with proper GRAND PRIX (not PRİX)
		const parts = n.split('Grand Prix');
		if (parts.length === 2) return parts[0].toUpperCase() + 'GRAND PRIX';
		return n.toUpperCase();
	}

	const RACE_EXTRAS = {
		'2026-australia': { temp: 23, rainfall: false, sc: '3 VSC', fastest: '1:19.813', fastestDriver: 'NOR' },
		'2026-china': { temp: 18, rainfall: false, sc: '1 SC', fastest: '1:35.902', fastestDriver: 'VER' },
	};

	function getTeamColor(dc) { return TEAM_COLORS[DRIVER_TEAMS[dc]] || '#6B7280'; }
	function formatDate(d) { return new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: '2-digit' }); }
	function formatDateShort(d) { return new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }).toUpperCase(); }
	function isCompleted(c) { return races.some(r => r.date === c.date); }
	function getRaceId(c) { const r = races.find(r => r.date === c.date); return r ? r.id : null; }



	let hoveredCard = $state(null);
	let sidebarOpen = $state(false);    // mobile drawer
	let sidebarCollapsed = $state(true); // desktop collapse
</script>

<svelte:head>
	<title>RaceRead - {tr.tagline}</title>
	<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
</svelte:head>

<div class="prv">

	<!-- NAV -->
	<nav class="prv-nav">
		<div class="prv-nav__inner">
			<div class="prv-nav__left">
				<button class="prv-nav__burger" onclick={() => sidebarOpen = !sidebarOpen}>
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
			onmouseenter={() => { clearTimeout(window.__sbTimer); sidebarCollapsed = false; }}
			onmouseleave={() => { window.__sbTimer = setTimeout(() => { sidebarCollapsed = true; }, 300); }}>

			<!-- Toggle button -->
			<button class="prv-sidebar__toggle" onclick={() => sidebarCollapsed = !sidebarCollapsed} title={sidebarCollapsed ? 'Expand' : 'Collapse'}>
				<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
					<path d={sidebarCollapsed ? 'M6 3l5 5-5 5' : 'M10 3L5 8l5 5'} stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
				</svg>
			</button>

			<div class="prv-sidebar__content">
				<!-- Season -->
				<div class="prv-sidebar__section">
					<h2 class="prv-sidebar__heading">{tr.sidebar_season}</h2>
					<p class="prv-sidebar__version">{tr.round} {races.length} / {CALENDAR_2026.length}</p>
				</div>

				<!-- Races -->
				<div class="prv-sidebar__section">
					<p class="prv-sidebar__label">{tr.sidebar_races}</p>
					<nav class="prv-sidebar__nav">
						{#each races as race, i}
							<a href="/race/{race.id}" class="prv-sidebar__race" onclick={() => sidebarOpen = false}>
								<span class="prv-sidebar__race-code">R{String(i + 1).padStart(2, '0')}</span>
								<span class="prv-sidebar__race-name">{race.circuit}</span>
								<span class="prv-sidebar__race-winner" style="color:{getTeamColor(race.winner)}">{race.winner}</span>
							</a>
						{/each}
						{#each CALENDAR_2026.filter(c => !isCompleted(c)).slice(0, 2) as next}
							<div class="prv-sidebar__race prv-sidebar__race--upcoming">
								<span class="prv-sidebar__race-code">R{String(next.round).padStart(2, '0')}</span>
								<span class="prv-sidebar__race-name">{next.code}</span>
								<span class="prv-sidebar__race-date">{formatDateShort(next.date)}</span>
							</div>
						{/each}
					</nav>
				</div>

				<!-- About link -->
				<div class="prv-sidebar__section prv-sidebar__section--last">
					<a href="/about" class="prv-sidebar__about-link">
						<span>{tr.sidebar_about}</span>
						<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
					</a>
				</div>

				<!-- Status -->
				<div class="prv-sidebar__bottom">
					<div class="prv-sidebar__status">
						<div class="prv-sidebar__dot"></div>
						<div>
							<p class="prv-sidebar__status-label">{tr.sidebar_status}</p>
							<p class="prv-sidebar__status-value">{tr.sidebar_active}</p>
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
					<span class="prv-hero__tagline">{tr.tagline}</span>
					<h1 class="prv-hero__title">
						{tr.headline_1}<br />
						<span class="prv-hero__title--accent">{tr.headline_2}</span>
					</h1>
					<p class="prv-hero__desc">{tr.desc}</p>
					<div class="prv-hero__actions">
						<a href="#races" class="prv-btn prv-btn--primary">{tr.cta_analyze}</a>
						<a href="/how" class="prv-btn prv-btn--ghost">{tr.cta_docs}</a>
					</div>
				</div>
			</section>

			<section class="prv-timeline">
				<div class="prv-timeline__header">
					<h3 class="prv-timeline__title">{tr.season_title}</h3>
					<p class="prv-timeline__sub">{tr.round} {races.length} / {CALENDAR_2026.length}</p>
				</div>
				<div class="prv-timeline__track">
					<div class="prv-timeline__line"></div>
					<div class="prv-timeline__progress" style="width: {(races.length / CALENDAR_2026.length) * 100}%"></div>
					<div class="prv-timeline__points">
						{#each CALENDAR_2026 as cal}
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

			<section class="prv-races" id="races">
				<div class="prv-races__grid">
					{#each races as race, i}
						{@const extras = RACE_EXTRAS[race.id] || {}}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<a href="/race/{race.id}" class="prv-card"
							onmouseenter={() => hoveredCard = race.id}
							onmouseleave={() => hoveredCard = null}>
							<div class="prv-card__top">
								<p class="prv-card__round">R{String(i + 1).padStart(2, '0')} / {formatDate(race.date)}</p>
								<h4 class="prv-card__name">{raceName(race.name)}</h4>
							</div>
							<div class="prv-card__info">
								<div class="prv-card__winner">
									<div class="prv-card__team-bar" style="background:{getTeamColor(race.winner)}"></div>
									<span class="prv-card__winner-text">{tr.winner}: {DRIVER_NAMES[race.winner] || race.winner}</span>
								</div>
								<div class="prv-card__meta">
									<span>{race.total_laps} {tr.laps_label}</span>
									{#if extras.temp}<span>{extras.temp + '\u00B0C'}</span>{/if}
									<span>{extras.rainfall === false ? 'DRY' : extras.rainfall ? 'WET' : ''}</span>
								</div>
							</div>
							<div class="prv-card__overlay" class:prv-card__overlay--visible={hoveredCard === race.id}>
								<div class="prv-card__stats">
									{#if extras.fastest}
										<div class="prv-card__stat">
											<span class="prv-card__stat-label">{tr.fastest_lap}</span>
											<span class="prv-card__stat-value">{extras.fastest} <span class="prv-card__stat-sub">({extras.fastestDriver})</span></span>
										</div>
									{/if}
									{#if extras.sc}
										<div class="prv-card__stat">
											<span class="prv-card__stat-label">{tr.safety_cars}</span>
											<span class="prv-card__stat-value">{extras.sc}</span>
										</div>
									{/if}
								</div>
								<div class="prv-card__cta">{tr.analyze} <span class="prv-card__arrow">&rarr;</span></div>
							</div>
						</a>
					{/each}
					{#each CALENDAR_2026.filter(c => !isCompleted(c)).slice(0, 1) as next}
						<div class="prv-card prv-card--upcoming">
							<div class="prv-card__top">
								<p class="prv-card__round prv-card__round--muted">{tr.upcoming} / {formatDate(next.date)}</p>
								<h4 class="prv-card__name prv-card__name--dim">{next.name}</h4>
							</div>
							<div class="prv-card__pending">{tr.no_data}</div>
						</div>
					{/each}
				</div>
			</section>

			<footer class="prv-footer">
				<span class="prv-footer__copy">{tr.footer_copy}</span>
				<div class="prv-footer__links">
					<span>{tr.footer_data}</span>
					<span>{tr.footer_energy}</span>
				</div>
			</footer>
		</div>
	</div>
</div>

<style>
	.prv {
		--p-bg: #0F1117; --p-bg2: #1A1D27; --p-bgc: #22252F;
		--p-t: #E8E8ED; --p-t2: #9CA3AF; --p-tm: #6B7280;
		--p-brd: #2E3240; --p-ac: #E24B4A; --p-ach: #C93B3A;
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
	.prv-sidebar__version { font-family: var(--p-fm); font-size: 10px; color: var(--p-ac); letter-spacing: .08em; text-transform: uppercase; margin-top: 3px; }
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
	.prv-btn--primary { background: var(--p-ac); color: #fff; }
	.prv-btn--primary:hover { background: var(--p-ach); }
	.prv-btn--ghost { background: none; border: 1px solid var(--p-brd); color: var(--p-t); }
	.prv-btn--ghost:hover { background: var(--p-bg2); }

	/* ── TIMELINE ── */
	.prv-timeline { background: var(--p-bg2); padding: 2.5rem 3rem; }
	.prv-timeline__header { margin-bottom: 1.5rem; }
	.prv-timeline__title { font-family: var(--p-fh); font-weight: 700; font-size: 22px; text-transform: uppercase; }
	.prv-timeline__sub { font-family: var(--p-fm); font-size: 11px; color: var(--p-ac); letter-spacing: .12em; text-transform: uppercase; margin-top: 3px; }
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
	.prv-timeline__code { font-family: var(--p-fm); font-size: 10px; text-transform: uppercase; color: var(--p-tm); }
	.prv-timeline__point--done .prv-timeline__code { color: var(--p-t); font-weight: 700; }

	/* ── CARDS ── */
	.prv-races { padding: 2.5rem 3rem; }
	.prv-races__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 2px; }
	.prv-card { position: relative; overflow: hidden; background: var(--p-bg2); padding: 1.5rem; display: flex; flex-direction: column; min-height: 170px; text-decoration: none; color: inherit; transition: background .2s, border-color .2s; border: 1px solid transparent; }
	.prv-card:hover { background: var(--p-bgc); border-color: rgba(226,75,74,.2); text-decoration: none; }
	.prv-card--upcoming { background: var(--p-bg); border: 1px solid var(--p-brd); }
	.prv-card__top { margin-bottom: 1.25rem; }
	.prv-card__round { font-family: var(--p-fm); font-size: 10px; color: var(--p-ac); }
	.prv-card__round--muted { color: var(--p-tm); }
	.prv-card__name { font-family: var(--p-fh); font-weight: 700; font-size: 18px; text-transform: uppercase; line-height: 1.2; margin-top: 5px; }
	.prv-card__name--dim { opacity: .35; }
	.prv-card__info { margin-top: auto; }
	.prv-card__winner { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
	.prv-card__team-bar { width: 3px; height: 16px; flex-shrink: 0; }
	.prv-card__winner-text { font-family: var(--p-fm); font-size: 11px; text-transform: uppercase; }
	.prv-card__meta { display: flex; gap: 1rem; font-family: var(--p-fm); font-size: 10px; color: var(--p-tm); text-transform: uppercase; }
	.prv-card__pending { margin-top: auto; font-family: var(--p-fm); font-size: 10px; color: var(--p-tm); text-transform: uppercase; letter-spacing: .1em; opacity: .4; }
	.prv-card__overlay { position: absolute; inset: auto 0 0 0; background: var(--p-bgc); padding: 1.25rem 1.5rem; transform: translateY(100%); transition: transform .25s ease; border-top: 1px solid rgba(226,75,74,.15); }
	.prv-card__overlay--visible { transform: translateY(0); }
	.prv-card__stats { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; margin-bottom: .75rem; }
	.prv-card__stat-label { display: block; font-family: var(--p-fm); font-size: 9px; color: var(--p-ac); text-transform: uppercase; margin-bottom: 2px; }
	.prv-card__stat-value { font-family: var(--p-fm); font-size: 12px; font-weight: 700; }
	.prv-card__stat-sub { font-size: 9px; opacity: .5; }
	.prv-card__cta { display: flex; align-items: center; justify-content: flex-end; gap: 6px; font-family: var(--p-fh); font-weight: 700; font-size: 10px; color: var(--p-ac); text-transform: uppercase; letter-spacing: .08em; }
	.prv-card__arrow { transition: transform .15s; }
	.prv-card:hover .prv-card__arrow { transform: translateX(3px); }

	/* ── FOOTER ── */
	.prv-sidebar__about-link {
		display: flex; align-items: center; justify-content: space-between;
		font-family: var(--p-fm); font-size: 11px; color: var(--p-t2);
		text-decoration: none; text-transform: uppercase; letter-spacing: .08em;
		padding: .4rem 0; transition: color .15s;
	}
	.prv-sidebar__about-link:hover { color: var(--p-ac); text-decoration: none; }

	.prv-footer { background: #0A0C12; padding: 1.5rem 3rem; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(46,50,64,.5); }
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
</style>
