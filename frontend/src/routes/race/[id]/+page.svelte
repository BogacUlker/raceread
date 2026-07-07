<script>
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { afterNavigate, replaceState } from '$app/navigation';
	import { t, locale } from '$lib/i18n/index.js';
	import { selectedDrivers, activeSession, showAnnotations } from '$lib/stores/race.js';
	import { collapsedSections } from '$lib/stores/dashboard.js';
	import { favoriteDriver } from '$lib/stores/prefs.js';
	import { TEAM_COLORS, localizedRaceName } from '$lib/constants.js';
	import { api } from '$lib/api.js';

	import DriverFilter from '$lib/components/layout/DriverFilter.svelte';
	import SessionToggle from '$lib/components/layout/SessionToggle.svelte';
	import ChartNav from '$lib/components/layout/ChartNav.svelte';
	import RaceInsightsPanel from '$lib/components/RaceInsightsPanel.svelte';
	import KeyMoments from '$lib/components/KeyMoments.svelte';
	import PaceChart from '$lib/components/charts/PaceChart.svelte';
	import SummarizedPace from '$lib/components/charts/SummarizedPace.svelte';
	import StrategyTimeline from '$lib/components/charts/StrategyTimeline.svelte';
	import DeltaMatrix from '$lib/components/charts/DeltaMatrix.svelte';
	import InferredBadge from '$lib/components/ui/InferredBadge.svelte';
	import QualifyingResults from '$lib/components/charts/QualifyingResults.svelte';
	import SectorComparison from '$lib/components/charts/SectorComparison.svelte';
	import QualifyingDelta from '$lib/components/charts/QualifyingDelta.svelte';
	import PitStopStats from '$lib/components/charts/PitStopStats.svelte';
	import IdealLaps from '$lib/components/charts/IdealLaps.svelte';
	import ExportButton from '$lib/components/ui/ExportButton.svelte';
	import SpeedTrapCard from '$lib/components/charts/SpeedTrapCard.svelte';
	import MetronomCard from '$lib/components/charts/MetronomCard.svelte';
	import TireDegChart from '$lib/components/charts/TireDegChart.svelte';
	import BattlesCard from '$lib/components/charts/BattlesCard.svelte';
	import WhatIfPanel from '$lib/components/charts/WhatIfPanel.svelte';
	import WeatherStrip from '$lib/components/ui/WeatherStrip.svelte';
	import { computeUndercuts, computeBattles, derivedMoments } from '$lib/analysis.js';

	let { data } = $props();
	let raceId = $derived(data.raceId);
	let raceInfo = $derived(data.raceInfo);
	let laps = $derived(data.laps);
	let strategy = $derived(data.strategy);
	let delta = $derived(data.delta);
	let annotations = $derived(data.annotations);
	let energyComparison = $derived(data.energyComparison);
	let pitstops = $derived(data.pitstops);
	let races = $derived(data.races || []);

	// Same logic as original dashboard
	let qualifyingData = $state(null), qualifyingLoading = $state(false), qualifyingError = $state(false);
	$effect(() => { if ($activeSession === 'qualifying' && qualifyingData === null && !qualifyingLoading) loadQualifying(); });
	async function loadQualifying() {
		qualifyingLoading = true; qualifyingError = false;
		try { qualifyingData = await api(`/api/races/${raceId}/qualifying`); } catch { qualifyingError = true; } finally { qualifyingLoading = false; }
	}

	let driverList = $derived(laps.map(d => {
		const last = d.laps.filter(l => l.position != null).at(-1);
		const pos = last?.position ?? 99;
		const isDNF = d.laps.length < (raceInfo.total_laps || 58) * 0.9;
		return { driver: d.driver, team: d.team, _pos: isDNF ? 100 + pos : pos };
	}).sort((a, b) => a._pos - b._pos));
	let teamsMap = $derived(Object.fromEntries(laps.map(d => [d.driver, d.team])));
	let finalPosMap = $derived(Object.fromEntries(laps.map(d => {
		const last = d.laps.filter(l => l.position != null).at(-1);
		const pos = last?.position ?? 99;
		const isDNF = d.laps.length < (raceInfo.total_laps || 58) * 0.9;
		return [d.driver, isDNF ? 100 + (raceInfo.total_laps - d.laps.length) : pos];
	})));
	let strategySorted = $derived([...(strategy.drivers || [])].sort((a, b) => (finalPosMap[a.driver] ?? 99) - (finalPosMap[b.driver] ?? 99)));
	let defaultSelected = $derived.by(() => {
		const top = laps.map(d => {
			const last = d.laps.filter(l => l.position != null).at(-1);
			return { driver: d.driver, pos: last?.position ?? 99 };
		}).sort((a, b) => a.pos - b.pos).slice(0, 10).map(d => d.driver);
		// favorite driver is always part of the default selection
		const fav = $favoriteDriver;
		if (fav && laps.some(d => d.driver === fav) && !top.includes(fav)) {
			return [...top.slice(0, 9), fav];
		}
		return top;
	});

	// Deep links: ?drivers=RUS,VER&session=qualifying (read once, then kept in sync)
	const _sp = browser ? new URLSearchParams(location.search) : null;
	const _urlDrivers = _sp?.get('drivers')?.split(',').map(s => s.trim().toUpperCase()).filter(Boolean) ?? null;
	if (_sp?.get('session') === 'qualifying') activeSession.set('qualifying');

	let initialized = $state(false);
	$effect(() => {
		if (initialized) return;
		const valid = _urlDrivers?.filter(d => laps.some(x => x.driver === d)) ?? [];
		if (valid.length > 0) {
			selectedDrivers.set(valid);
			initialized = true;
		} else if ($selectedDrivers.length === 0 && defaultSelected.length > 0) {
			selectedDrivers.set(defaultSelected);
			initialized = true;
		} else if ($selectedDrivers.length > 0) {
			initialized = true;
		}
	});

	// Keep the URL shareable as selection/session change (replaceState = no reloads).
	// afterNavigate guard: replaceState throws until the router is initialized.
	let mounted = $state(false);
	afterNavigate(() => { mounted = true; });
	$effect(() => {
		if (!browser || !initialized || !mounted) return;
		const sel = $selectedDrivers.join(',');
		const session = $activeSession;
		const p = new URLSearchParams(location.search);
		if (sel) p.set('drivers', sel); else p.delete('drivers');
		if (session === 'qualifying') p.set('session', 'qualifying'); else p.delete('session');
		const qs = p.toString();
		const next = (qs ? '?' + qs : location.pathname) + location.hash;
		if (location.search !== (qs ? '?' + qs : '')) replaceState(next, {});
	});

	let vscLaps = $derived(data.vscData?.vsc_laps || []);
	let scLaps = $derived(data.vscData?.sc_laps || []);


	// Sidebar state
	
	// Uppercase race name with proper GRAND PRIX (not PRİX)
	function fmtLap(s) {
		if (s == null) return '-';
		const m = Math.floor(s / 60);
		const sec = s % 60;
		return m > 0 ? m + ':' + sec.toFixed(3).padStart(6, '0') : sec.toFixed(3);
	}

	function gpName(name) {
		if (!name) return '';
		const n = localizedRaceName(name, $locale);
		const parts = n.split('Grand Prix');
		if (parts.length === 2) return parts[0].toLocaleUpperCase($locale === 'tr' ? 'tr' : 'en') + 'GRAND PRIX';
		return n.toUpperCase();
	}

	let story = $derived(data.story);

	let sidebarCollapsed = $state(true);

	// Overview computed stats
	let scEventCount = $derived.by(() => {
		// Count distinct SC/VSC deployments (not individual laps)
		// vscLaps/scLaps are arrays of lap numbers under that condition
		let vscCount = 0;
		let scCount = 0;
		// Count groups of consecutive laps as one event
		if (vscLaps.length > 0) {
			vscCount = 1;
			const sorted = [...vscLaps].sort((a, b) => a - b);
			for (let i = 1; i < sorted.length; i++) {
				if (sorted[i] - sorted[i-1] > 2) vscCount++;
			}
		}
		if (scLaps.length > 0) {
			scCount = 1;
			const sorted = [...scLaps].sort((a, b) => a - b);
			for (let i = 1; i < sorted.length; i++) {
				if (sorted[i] - sorted[i-1] > 2) scCount++;
			}
		}
		return { vscCount, scCount, vscLaps: vscLaps.length, scLaps: scLaps.length, total: vscLaps.length + scLaps.length };
	});

	let scDisplay = $derived.by(() => {
		const e = scEventCount;
		if (e.total === 0) return { main: '-', sub: '' };
		const parts = [];
		if (e.scCount > 0) parts.push(e.scCount + ' SC');
		if (e.vscCount > 0) parts.push(e.vscCount + ' VSC');
		return { main: parts.join(' + '), sub: e.total + ($locale === 'tr' ? ' tur' : ' laps') };
	});

	let winnerMargin = $derived.by(() => {
		if (!delta?.drivers?.length || !delta?.matrix?.length) return null;
		const wi = delta.drivers.indexOf(raceInfo.winner);
		if (wi < 0) return null;
		const second = delta.matrix[wi]?.find((v, i) => i !== wi && v !== null && v !== 0);
		return second ? Math.abs(second).toFixed(3) : null;
	});

	// Fastest lap across all drivers (backend extras carry full precision;
	// the laps API rounds time_s, so prefer raceInfo when present)
	let fastestLap = $derived.by(() => {
		if (raceInfo.fastest_lap_s) {
			return { driver: raceInfo.fastest_driver, time: raceInfo.fastest_lap_s, lap: raceInfo.fastest_lap_no };
		}
		let best = null;
		for (const driver of laps) {
			for (const lap of (driver.laps || [])) {
				if (lap.time_s && lap.is_accurate !== false && lap.lap > 1) {
					if (!best || lap.time_s < best.time) {
						best = { driver: driver.driver, time: lap.time_s, lap: lap.lap };
					}
				}
			}
		}
		return best;
	});

	// Best D/C ratio
	let bestDC = $derived.by(() => {
		const entries = energyComparison?.entries || [];
		if (!entries.length) return null;
		const best = entries.reduce((a, b) => (a.dc_ratio || 0) > (b.dc_ratio || 0) ? a : b);
		return best.dc_ratio ? { driver: best.driver, ratio: best.dc_ratio } : null;
	});

	// Team color helper
	function tc(driver) { return TEAM_COLORS[teamsMap[driver]] || '#6B7280'; }

	// Data-derived insights: undercut cycles + sustained battles
	let traffic = $state(null);
	$effect(() => {
		const id = raceId;
		if (!id || typeof window === 'undefined') return;
		traffic = null;
		api(`/api/races/${id}/traffic`).then((d) => { if (id === raceId) traffic = d; }).catch(() => {});
	});
	let undercuts = $derived(computeUndercuts(laps, strategy, vscLaps, scLaps));
	let battles = $derived(traffic ? computeBattles(traffic, laps, strategy) : []);
	let momentsAll = $derived([
		...(annotations.annotations || []),
		...derivedMoments(undercuts, battles),
	]);

	// Prev/next race navigation - classics navigate within the classics shelf
	let calendar = $derived(data.calendar || []);
	let classics = $derived(data.classics || []);
	let isClassic = $derived(classics.some(c => c.id === raceId));
	let navList = $derived(isClassic ? classics : races);
	let raceIdx = $derived(navList.findIndex(r => r.id === raceId));
	let prevRace = $derived(raceIdx > 0 ? navList[raceIdx - 1] : null);
	let nextRace = $derived(raceIdx >= 0 && raceIdx < navList.length - 1 ? navList[raceIdx + 1] : null);

	// Scroll-triggered reveal animation
	
	onMount(() => {
		const observer = new IntersectionObserver((entries) => {
			entries.forEach(entry => {
				if (entry.isIntersecting) {
					entry.target.classList.add('pd-visible');
					observer.unobserve(entry.target);
				}
			});
		}, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

		// Observe all chart cards and sections
		document.querySelectorAll('.pd-ov-card, .pd-sec').forEach(el => {
			observer.observe(el);
		});

		// Scroll happens inside .pd-main, so honor #section-* hashes manually
		if (location.hash) {
			const el = document.querySelector(location.hash);
			if (el) setTimeout(() => el.scrollIntoView({ block: 'start' }), 50);
		}

		return () => observer.disconnect();
	});

</script>

<svelte:head>
	<title>{raceInfo.name} - RaceRead</title>
	
</svelte:head>

<div class="pd">
	<!-- NAV -->
	<nav class="pd-nav">
		<div class="pd-nav__inner">
			<div class="pd-nav__left">
				<button class="pd-nav__burger" aria-label={$locale === 'tr' ? 'Yarış listesini aç/kapat' : 'Toggle race list'} onclick={() => sidebarCollapsed = !sidebarCollapsed}>
					<span></span><span></span><span></span>
				</button>
				<a href="/" class="pd-nav__logo"><img src="/logo@2x.png" alt="RaceRead" class="pd-nav__logo-img" /></a>
			</div>
			<button class="pd-nav__lang" onclick={() => locale.set($locale === 'en' ? 'tr' : 'en')}>
				{$locale === 'en' ? 'TR' : 'EN'}
			</button>
		</div>
	</nav>

	<div class="pd-layout">
		<!-- SIDEBAR -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<aside class="pd-sb" class:collapsed={sidebarCollapsed}
			onmouseenter={() => { clearTimeout(window.__sbTimer); sidebarCollapsed = false; }}
			onmouseleave={() => { window.__sbTimer = setTimeout(() => { sidebarCollapsed = true; }, 300); }}>
			<button class="pd-sb__toggle" onclick={() => sidebarCollapsed = !sidebarCollapsed}>
				<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
					<path d={sidebarCollapsed ? 'M6 3l5 5-5 5' : 'M10 3L5 8l5 5'} stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
				</svg>
			</button>
			<div class="pd-sb__full">
				<div class="pd-sb__sec">
					<h2 class="pd-sb__h">{isClassic ? $t('home.classics_title') : '2026 ' + ($locale === 'tr' ? 'Sezonu' : 'Season')}</h2>
					<p class="pd-sb__sub">{isClassic ? classics.length : races.length + (calendar.length ? ' / ' + calendar.length : '')}</p>
				</div>
				<div class="pd-sb__sec">
					<nav class="pd-sb__nav">
						{#if isClassic}
							{#each classics as c}
								<a href="/race/{c.id}" class="pd-sb__race" class:pd-sb__race--active={c.id === raceId}>
									<span class="pd-sb__rc">'{String(c.year).slice(2)}</span>
									<span class="pd-sb__rn">{c.circuit}</span>
									<span class="pd-sb__rw" style="color:{TEAM_COLORS[c.winner_team] || '#888'}">{c.winner}</span>
								</a>
							{/each}
						{:else}
							{#each races as race, i}
								<a href="/race/{race.id}" class="pd-sb__race" class:pd-sb__race--active={race.id === raceId}>
									<span class="pd-sb__rc">R{i + 1}</span>
									<span class="pd-sb__rn">{race.circuit}</span>
									<span class="pd-sb__rw" style="color:{tc(race.winner)}">{race.winner}</span>
								</a>
							{/each}
						{/if}
					</nav>
				</div>
				<div class="pd-sb__bottom">
					<a href="/" class="pd-sb__home">&larr; {$locale === 'tr' ? 'Ana Sayfa' : 'Home'}</a>
				</div>
			</div>
			<div class="pd-sb__mini">
				{#if isClassic}
					{#each classics as c}
						<a href="/race/{c.id}" class="pd-sb__mr" class:pd-sb__mr--active={c.id === raceId} title={c.name} style="border-left-color:{TEAM_COLORS[c.winner_team] || '#888'}">{c.code}</a>
					{/each}
				{:else}
					{#each races as race, i}
						<a href="/race/{race.id}" class="pd-sb__mr" class:pd-sb__mr--active={race.id === raceId} title={race.name} style="border-left-color:{tc(race.winner)}">R{i+1}</a>
					{/each}
				{/if}
			</div>
		</aside>

		<!-- MAIN -->
		<div class="pd-main">
			<!-- Header -->
			<div class="pd-header">
				<div class="pd-header__row">
					{#if prevRace}
						<a href="/race/{prevRace.id}" class="pd-header__arrow" title={prevRace.name}>&larr; <span class="pd-header__arrow-name">{prevRace.circuit}</span></a>
					{:else}
						<span class="pd-header__arrow pd-header__arrow--off">&larr;</span>
					{/if}
					<h1 class="pd-header__title">{gpName(raceInfo.name)}</h1>
					{#if nextRace}
						<a href="/race/{nextRace.id}" class="pd-header__arrow" title={nextRace.name}><span class="pd-header__arrow-name">{nextRace.circuit}</span> &rarr;</a>
					{:else}
						<span class="pd-header__arrow pd-header__arrow--off">&rarr;</span>
					{/if}
				</div>
				<div class="pd-header__meta">
					<span>{raceInfo.circuit}</span>
					<span class="pd-sep">/</span>
					<span>{raceInfo.date}</span>
					<span class="pd-sep">/</span>
					<span>{raceInfo.total_laps} {$t('race.laps')}</span>
					<span class="pd-sep">/</span>
					<span class="pd-winner">{$t('race.winner')}: {raceInfo.winner}</span>
				</div>
			</div>

			<!-- Race Story -->
			{#if story?.story_en}
				<div class="pd-story">
					<span class="pd-story__k">{$t('story.title')} &middot; AI</span>
					<p class="pd-story__text">{$locale === 'tr' && story.story_tr ? story.story_tr : story.story_en}</p>
				</div>
			{/if}

			<!-- Overview Cards -->
			<div class="pd-overview">
				<div class="pd-ov-card pd-ov-card--accent">
					<p class="pd-ov-label">SC / VSC</p>
					<p class="pd-ov-value">{scDisplay.main}</p>
					{#if scDisplay.sub}<p class="pd-ov-sub">{scDisplay.sub}</p>{/if}
				</div>
				<div class="pd-ov-card">
					<p class="pd-ov-label">{$locale === 'tr' ? 'Kazananın Farkı' : 'Winner Margin'}</p>
					<p class="pd-ov-value">{winnerMargin ? '+' + winnerMargin + 's' : 'N/A'}</p>
					<p class="pd-ov-sub">{raceInfo.winner} vs P2</p>
				</div>
				<div class="pd-ov-card">
					<p class="pd-ov-label">{$locale === 'tr' ? 'En Hızlı Tur' : 'Fastest Lap'}</p>
					<p class="pd-ov-value">{fastestLap ? fmtLap(fastestLap.time) : '-'}</p>
					<p class="pd-ov-sub" style="color:{fastestLap ? tc(fastestLap.driver) : ''}">{fastestLap ? fastestLap.driver + ' / L' + fastestLap.lap : ''}</p>
				</div>
				<div class="pd-ov-card">
					<p class="pd-ov-label">{$locale === 'tr' ? 'En İyi D/C Oranı' : 'Best D/C Ratio'}</p>
					<p class="pd-ov-value">{bestDC ? bestDC.ratio.toFixed(2) : '-'}</p>
					<p class="pd-ov-sub" style="color:{bestDC ? tc(bestDC.driver) : ''}">{bestDC ? bestDC.driver : ''}</p>
				</div>
			</div>

			<SessionToggle />

			{#if $activeSession === 'race'}
				<div class="pd-toolbar">
					<div class="pd-toolbar__filter">
						<DriverFilter drivers={driverList} selected={$selectedDrivers} onchange={(v) => selectedDrivers.set(v)} />
					</div>
					<div class="pd-toolbar__actions">
						<button class="pd-btn" class:active={$showAnnotations} onclick={() => showAnnotations.update(v => !v)}>
							{$t('annotations.toggle_label')} {$showAnnotations ? 'ON' : 'OFF'}
						</button>
						<a href="/race/{raceId}/replay" class="pd-btn">{$t('replay.room_title')}</a>
						{#if driverList.length >= 2}
							<a href="/race/{raceId}/compare" class="pd-btn">{$t('charts.compare')}</a>
						{/if}
						<a href="/race/{raceId}/broadcast" class="pd-btn pd-btn--accent">{$t('charts.broadcast')}</a>
					</div>
				</div>
			{/if}

			<ChartNav />

			{#if $activeSession === 'race'}
				<KeyMoments annotations={momentsAll} {raceId} radio={data.radio?.clips || []} {teamsMap} />

				{#if $showAnnotations}
					<div class="pd-sec"><RaceInsightsPanel annotations={annotations.annotations || []} /></div>
				{/if}

				<div class="pd-grid">
					<!-- 01. Pace -->
					<div id="section-pace" class="pd-sec">
						<ExportButton target="#section-pace" filename="{raceId}-pace" />
						<div class="pd-sec__body" class:collapsed={$collapsedSections['pace']}>
							<div class="pd-row pd-row--pace">
								<div class="pd-cell pd-cell--wide"><PaceChart {laps} selectedDrivers={$selectedDrivers} {vscLaps} {scLaps} annotations={$showAnnotations ? (annotations.annotations || []) : []} {strategy} /><WeatherStrip {raceId} totalLaps={raceInfo.total_laps} /></div>
								<div class="pd-cell pd-cell--side"><SummarizedPace {laps} /></div>
							</div>
						</div>
					</div>

					<!-- 02. Strategy -->
					<div id="section-strategy" class="pd-sec">
						<ExportButton target="#section-strategy" filename="{raceId}-strategy" />
						<div class="pd-sec__body" class:collapsed={$collapsedSections['strategy']}>
							<StrategyTimeline drivers={strategySorted} totalLaps={raceInfo.total_laps} {vscLaps} {scLaps} />
							<TireDegChart {laps} {vscLaps} {scLaps} />
							<WhatIfPanel {laps} {strategy} {raceInfo} {vscLaps} {scLaps} {teamsMap} {traffic} />
						</div>
					</div>

					<!-- 03. Pit Stops -->
					<div id="section-pit-stops" class="pd-sec">
						<ExportButton target="#section-pit-stops" filename="{raceId}-pitstops" />
						<div class="pd-sec__body" class:collapsed={$collapsedSections['pit-stops']}>
							<PitStopStats data={pitstops} />

						</div>
					</div>

					<!-- 04. Energy: delta matrix + room preview (full analysis lives in /energy) -->
					<div class="pd-sec pd-sec--split">
						{#if undercuts.length}
							<div class="pd-uc">
								<span class="pd-uc__title">{$t('insights.undercut_title')}</span>
								{#each undercuts.slice(0, 4) as u}
									{@const winner = u.gain > 0 ? u.first : u.second}
									{@const loser = u.gain > 0 ? u.second : u.first}
									<div class="pd-uc__row">
										<span class="pd-uc__lap">L{u.lap}</span>
										<span class="pd-uc__w" style="color:{tc(winner)}">{winner}</span>
										<span class="pd-uc__vs">{u.gain > 0 ? $t('insights.undercut_vs') : $t('insights.overcut_vs')}</span>
										<span class="pd-uc__l" style="color:{tc(loser)}">{loser}</span>
										<span class="pd-uc__gain">+{Math.abs(u.gain).toFixed(1)}s</span>
									</div>
								{/each}
							</div>
						{/if}
						<SpeedTrapCard {laps} />
						<MetronomCard {laps} {vscLaps} {scLaps} />
						<BattlesCard {battles} {teamsMap} />
					</div>

					<div id="section-energy" class="pd-sec">
						<ExportButton target="#section-energy" filename="{raceId}-energy" />
						<div class="pd-sec__body" class:collapsed={$collapsedSections['energy']}>
							<div class="pd-row pd-row--split">
								<div class="pd-cell"><DeltaMatrix drivers={delta.drivers || []} matrix={delta.matrix || []} teams={teamsMap} /></div>
								<div class="pd-cell">
									<a href="/race/{raceId}/energy" class="chart-card pd-roomcard">
										<div class="chart-card__header">
											<span class="chart-card__title">{$t('energy.room_title')}</span>
											<InferredBadge confidence={raceInfo.validation_confidence} />
										</div>
										<div class="pd-roomcard__bars">
											{#each (energyComparison.entries || []).slice(0, 10) as e}
												<div class="pd-roomcard__bar" style="height:{Math.min(100, (e.dc_ratio || 0) * 18)}%; background:{tc(e.driver)}" title="{e.driver} D/C {e.dc_ratio?.toFixed(2)}"></div>
											{/each}
										</div>
										<p class="pd-roomcard__desc">{$t('energy.room_desc')}</p>
										<span class="pd-roomcard__go">{$t('energy.explore')} &rarr;</span>
									</a>
								</div>
							</div>
						</div>
					</div>

					<!-- 05. Rooms: telemetry + replay -->
					<div id="section-telemetry" class="pd-sec">
						<div class="pd-row pd-row--split">
							<a href="/race/{raceId}/telemetry" class="chart-card pd-roomcard">
								<div class="chart-card__header">
									<span class="chart-card__title">{$t('telemetry.room_title')}</span>
								</div>
								<svg viewBox="0 0 300 90" class="pd-roomcard__viz" aria-hidden="true">
									<path d="M4,72 L30,20 C36,8 44,8 50,20 L66,58 C72,70 80,70 86,58 L104,18 C110,6 118,6 124,18 L140,52 C146,64 154,64 160,52 L182,14 C188,4 196,4 202,14 L222,60 C228,72 236,72 242,60 L262,26 C268,14 276,14 282,26 L296,54" fill="none" stroke="#3B82F6" stroke-width="2.5" opacity=".8"/>
									<path d="M4,80 L60,80 L70,64 L90,64 L100,80 L170,80 L180,64 L210,64 L220,80 L296,80" fill="none" stroke="var(--text-muted)" stroke-width="1.5" opacity=".5"/>
								</svg>
								<p class="pd-roomcard__desc">{$t('telemetry.room_desc')}</p>
								<span class="pd-roomcard__go">{$t('telemetry.explore')} &rarr;</span>
							</a>
							<a href="/race/{raceId}/replay" class="chart-card pd-roomcard">
								<div class="chart-card__header">
									<span class="chart-card__title">{$t('replay.room_title')}</span>
								</div>
								<div class="pd-roomcard__viz pd-roomcard__replay">
									<span class="pd-roomcard__playicon">&#9654;</span>
									<div class="pd-roomcard__track"><div class="pd-roomcard__prog"></div></div>
									<span class="pd-roomcard__laps">L1 &mdash; L{raceInfo.total_laps}</span>
								</div>
								<p class="pd-roomcard__desc">{$t('replay.room_desc')}</p>
								<span class="pd-roomcard__go">{$t('replay.watch')} &rarr;</span>
							</a>
						</div>
					</div>
				</div>
			{:else}
				{#if qualifyingLoading}
					<div class="pd-loading">{$t('common.loading')}</div>
				{:else if qualifyingError}
					<div class="pd-loading">{$t('common.no_data')}</div>
				{:else if qualifyingData}
					{#if $showAnnotations}<RaceInsightsPanel annotations={annotations.annotations || []} chartTypes={['qualifying']} />{/if}
					<div class="pd-grid">
						<div id="section-qualifying-results" class="pd-sec"><div class="pd-sec__body"><QualifyingResults drivers={qualifyingData.drivers || []} {raceId} /></div></div>
						<div id="section-sector-comparison" class="pd-sec"><div class="pd-sec__body"><SectorComparison drivers={qualifyingData.drivers || []} /></div></div>
						<div id="section-ideal-laps" class="pd-sec"><div class="pd-sec__body"><IdealLaps drivers={qualifyingData.drivers || []} /></div></div>
						<div id="section-qualifying-delta" class="pd-sec"><div class="pd-sec__body"><QualifyingDelta drivers={qualifyingData.drivers || []} /></div></div>
					</div>
				{/if}
			{/if}

			<!-- Footer -->
			<footer class="pd-footer">
				<div class="pd-footer__row">
					<div class="pd-footer__stats">
						<div><p class="pd-footer__label">Data Source</p><p class="pd-footer__val">FastF1 3.8.1</p></div>
						<div><p class="pd-footer__label">Calendar</p><p class="pd-footer__val">Jolpica-F1</p></div>
						<div><p class="pd-footer__label">Energy</p><p class="pd-footer__val pd-footer__val--accent">Inferred</p></div>
					</div>
					<p class="pd-footer__copy">{'\u00A9'} 2026 RACEREAD</p>
				</div>
				<p class="pd-footer__legal">{$t('footer.disclaimer')}</p>
			</footer>
		</div>
	</div>
</div>

<style>
	.pd {
		--bg: var(--bg-primary); --bg2: var(--bg-secondary); --bgc: var(--bg-card);
		--t: var(--text-primary); --t2: var(--text-secondary); --tm: #6B7280; --brd: var(--border);
		--ac: var(--accent); --ach: #C93B3A;
		--fh: var(--font-heading); --fb: var(--font-body); --fm: var(--font-mono);
		--sbw: 220px; --sbc: 44px;
		position: fixed; inset: 0; z-index: 200; overflow: hidden;
		background: var(--bg); color: var(--t); font-family: var(--fb);
		-webkit-font-smoothing: antialiased;
	}

	/* Global overrides - premium chart presentation */
	.pd :global(*) { border-radius: 0 !important; }

	/* Chart cards: tonal surface + hover glow + left accent */
	.pd :global(.chart-card) {
		border-radius: 0 !important;
		border: none !important;
		border-left: 2px solid transparent !important;
		background: var(--bg2) !important;
		transition: border-color .25s, box-shadow .25s, background .25s !important;
		position: relative;
	}
	.pd :global(.chart-card:hover) {
		border-left-color: var(--ac) !important;
		box-shadow: -4px 0 20px -4px rgba(226,75,74,.12), 0 0 40px -12px rgba(226,75,74,.06) !important;
		background: #1d2130 !important;
	}

	/* Chart titles: Space Grotesk + subtle separator */
	.pd :global(.chart-card__title) {
		font-family: var(--fh) !important;
		text-transform: uppercase;
		letter-spacing: .03em;
		font-size: 16px !important;
	}
	.pd :global(.chart-card__header) {
		border-bottom: 1px solid rgba(46,50,64,.3) !important;
		padding-bottom: 10px !important;
		margin-bottom: 14px !important;
	}

	/* Buttons & selects inside charts */
	.pd :global(.chart-card button),
	.pd :global(.chart-card select) {
		transition: border-color .15s, background .15s !important;
	}
	.pd :global(.chart-card button:hover),
	.pd :global(.chart-card select:hover) {
		border-color: rgba(226,75,74,.3) !important;
	}

	/* Dot-grid background texture on chart interiors */
	.pd :global(.chart-card)::before {
		content: '';
		position: absolute;
		inset: 0;
		background-image: radial-gradient(rgba(89,65,63,.08) 1px, transparent 1px);
		background-size: 16px 16px;
		pointer-events: none;
		z-index: 0;
		opacity: 0;
		transition: opacity .3s;
	}
	.pd :global(.chart-card:hover)::before {
		opacity: 1;
	}
	.pd :global(.chart-card > *) {
		position: relative;
		z-index: 1;
	}

	/* InferredBadge enhancement */
	.pd :global([class*="inferred"]) {
		letter-spacing: .06em !important;
	}

	/* Scrollbar styling within charts */
	.pd :global(.chart-card ::-webkit-scrollbar) { width: 3px; height: 3px; }
	.pd :global(.chart-card ::-webkit-scrollbar-thumb) { background: var(--brd); }

	/* NAV */
	.pd-nav { position: relative; z-index: 60; background: var(--bg); border-bottom: 1px solid rgba(46,50,64,.6); }
	.pd-nav__inner { padding: 0 1.25rem; height: 52px; display: flex; align-items: center; justify-content: space-between; }
	.pd-nav__left { display: flex; align-items: center; gap: 1rem; }
	.pd-nav__logo { display: flex; align-items: center; text-decoration: none; }
	.pd-nav__logo:hover { text-decoration: none; }
	.pd-nav__logo-img { height: 36px; width: auto; }
	.pd-nav__burger { display: none; flex-direction: column; gap: 4px; background: none; border: none; cursor: pointer; padding: 4px; }
	.pd-nav__burger span { display: block; width: 16px; height: 1.5px; background: var(--t2); }
	.pd-nav__lang { font-family: var(--fm); font-size: 10px; font-weight: 700; letter-spacing: .1em; color: var(--ac-text, var(--accent-text)); background: none; border: 1px solid var(--brd); padding: 4px 10px; cursor: pointer; }

	/* LAYOUT */
	.pd-layout { display: flex; height: calc(100vh - 52px); }

	/* SIDEBAR */
	.pd-sb {
		width: var(--sbw); min-width: var(--sbw); background: var(--bg2);
		border-right: 1px solid rgba(46,50,64,.5); display: flex; flex-direction: column;
		position: relative; z-index: 55; overflow: hidden;
		transition: width .25s ease, min-width .25s ease;
	}
	.pd-sb.collapsed { width: var(--sbc); min-width: var(--sbc); }
	.pd-sb__toggle { position: absolute; top: 10px; right: 6px; z-index: 5; width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; background: var(--bg2); border: 1px solid rgba(46,50,64,.5); color: var(--tm); cursor: pointer; transition: all .2s; }
	.pd-sb__toggle:hover { color: var(--t); }
	.collapsed .pd-sb__toggle { right: auto; left: 50%; transform: translateX(-50%); }
	/* Full content: visible when expanded */
	.pd-sb__full { display: flex; flex-direction: column; flex: 1; overflow-y: auto; white-space: nowrap; opacity: 1; transition: opacity .2s ease .1s; }
	.collapsed .pd-sb__full { opacity: 0; pointer-events: none; transition: opacity .15s ease 0s; }
	/* Mini: visible when collapsed */
	.pd-sb__mini { display: flex; flex-direction: column; align-items: center; gap: 4px; padding-top: 44px; position: absolute; top: 0; left: 0; right: 0; bottom: 0; opacity: 0; pointer-events: none; transition: opacity .15s ease 0s; }
	.collapsed .pd-sb__mini { opacity: 1; pointer-events: auto; transition: opacity .2s ease .15s; }
	.pd-sb__sec { padding: 1rem; border-bottom: 1px solid rgba(46,50,64,.4); }
	.pd-sb__h { font-family: var(--fh); font-weight: 700; font-size: 13px; text-transform: uppercase; }
	.pd-sb__sub { font-family: var(--fm); font-size: 10px; color: var(--ac-text, var(--accent-text)); margin-top: 2px; }
	.pd-sb__nav { display: flex; flex-direction: column; gap: 1px; }
	.pd-sb__race { display: flex; align-items: center; gap: .4rem; padding: .4rem .5rem; text-decoration: none; color: inherit; font-family: var(--fm); font-size: 11px; transition: background .15s; }
	.pd-sb__race:hover { background: rgba(226,75,74,.08); text-decoration: none; }
	.pd-sb__race--active { background: rgba(226,75,74,.12); border-left: 2px solid var(--ac); }
	.pd-sb__rc { font-size: 10px; color: var(--ac-text, var(--accent-text)); min-width: 22px; }
	.pd-sb__rn { flex: 1; }
	.pd-sb__rw { font-size: 10px; font-weight: 700; }
	.pd-sb__bottom { margin-top: auto; padding: 1rem; border-top: 1px solid rgba(46,50,64,.4); }
	.pd-sb__home { font-family: var(--fm); font-size: 10px; color: var(--ac-text, var(--accent-text)); text-decoration: none; text-transform: uppercase; letter-spacing: .08em; }
	.pd-sb__home:hover { text-decoration: none; opacity: .8; }
	.pd-sb__mr { font-family: var(--fm); font-size: 9.5px; font-weight: 700; color: var(--t2); text-decoration: none; padding: 3px 0; border-left: 2px solid transparent; padding-left: 6px; width: 34px; text-align: center; }
	.pd-sb__mr:hover { color: var(--ac-text, var(--accent-text)); text-decoration: none; }
	.pd-sb__mr--active { color: var(--ac-text, var(--accent-text)); border-left-color: var(--ac-text, var(--accent-text)); }

	/* MAIN */
	.pd-main { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 1.5rem 2rem 3rem; }

	/* HEADER */
	.pd-header { margin-bottom: 1.25rem; }
	.pd-header__row { display: flex; align-items: baseline; gap: 14px; }
	.pd-header__title { font-family: var(--fh); font-weight: 700; font-size: 26px; letter-spacing: -.02em; margin-bottom: 4px; }
	.pd-header__arrow { font-family: var(--fm); font-size: 11px; color: var(--tm); text-decoration: none; white-space: nowrap; transition: color .15s; }
	.pd-header__arrow:hover { color: var(--ac-text, var(--accent-text)); text-decoration: none; }
	.pd-header__arrow--off { opacity: .25; }
	@media (max-width: 640px) { .pd-header__arrow-name { display: none; } }
	.pd-header__meta { display: flex; align-items: center; gap: 6px; font-family: var(--fm); font-size: 11px; color: var(--t2); }
	.pd-sep { color: var(--tm); }
	.pd-winner { color: var(--ac-text, var(--accent-text)); font-weight: 600; }

	/* ENERGY ROOM PREVIEW CARD */
	.pd-roomcard { display: flex; flex-direction: column; height: 100%; padding: 16px; text-decoration: none; color: inherit; cursor: pointer; }
	.pd-roomcard:hover { text-decoration: none; }
	.pd-roomcard__bars { display: flex; align-items: flex-end; gap: 6px; height: 130px; margin: 12px 0 4px; }
	.pd-roomcard__bar { flex: 1; min-height: 4px; opacity: .85; transition: opacity .15s; }
	.pd-roomcard:hover .pd-roomcard__bar { opacity: 1; }
	.pd-roomcard__desc { font-size: 12.5px; line-height: 1.55; color: var(--t2); margin: 8px 0 12px; }
	.pd-roomcard__go { margin-top: auto; align-self: flex-start; font-family: var(--fm); font-size: 10px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #F07B7A; border: 1px solid rgba(226,75,74,.35); padding: 5px 12px; transition: background .15s, color .15s; }
	.pd-roomcard:hover .pd-roomcard__go { background: var(--ac); color: #fff; }
	.pd-roomcard__viz { width: 100%; height: 90px; margin: 10px 0 2px; }
	.pd-roomcard__replay { display: flex; align-items: center; gap: 12px; }
	.pd-roomcard__playicon { width: 34px; height: 34px; background: var(--ac); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 12px; flex-shrink: 0; }
	.pd-roomcard__track { flex: 1; height: 4px; background: var(--bgc); position: relative; }
	.pd-roomcard__prog { position: absolute; left: 0; top: 0; bottom: 0; width: 55%; background: var(--ac); }
	.pd-roomcard__laps { font-family: var(--fm); font-size: 10px; color: var(--tm); white-space: nowrap; }

	/* RACE STORY */
	.pd-story { background: var(--bg2); border-left: 3px solid var(--ac); padding: 1rem 1.4rem; margin-bottom: 1rem; }
	.pd-story__k { font-family: var(--fm); font-size: 10px; color: #F07B7A; letter-spacing: .12em; text-transform: uppercase; }
	.pd-story__text { font-size: 13.5px; line-height: 1.65; color: var(--t2); margin-top: 6px; max-width: 95ch; }
	.pd-story__text::first-line { color: var(--t); }

	/* OVERVIEW CARDS */
	.pd-overview { display: grid; grid-template-columns: repeat(4, 1fr); gap: 2px; margin-bottom: 1.5rem; }
	.pd-ov-card { background: var(--bg2); padding: 1.25rem 1.5rem; border-left: 3px solid var(--brd); position: relative; overflow: hidden; transition: border-color .2s; }
	.pd-ov-card:hover { border-left-color: var(--ac-text, var(--accent-text)); }
	.pd-ov-card--accent { border-left-color: var(--ac-text, var(--accent-text)); background: linear-gradient(135deg, var(--bg2) 0%, rgba(226,75,74,.06) 100%); }
	.pd-ov-label { font-family: var(--fm); font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: .1em; margin-bottom: .6rem; font-weight: 600; }
	.pd-ov-value { font-family: var(--fh); font-size: 28px; font-weight: 900; font-style: italic; line-height: 1; letter-spacing: 0; margin: 0; }
	.pd-ov-card--accent .pd-ov-value { color: var(--ac-text, var(--accent-text)); }
	.pd-ov-sub { font-family: var(--fm); font-size: 12px; color: var(--text-secondary); margin-top: 6px; text-transform: uppercase; letter-spacing: .04em; }

	/* TOOLBAR */
	.pd-toolbar { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }
	.pd-toolbar__filter { flex: 1; }
	.pd-toolbar__actions { display: flex; gap: 6px; flex-shrink: 0; padding-top: 2px; }
	.pd-btn { font-family: var(--fm); font-size: 11px; color: var(--t2); padding: 5px 10px; border: 1px solid rgba(46,50,64,.6); background: none; text-decoration: none; cursor: pointer; white-space: nowrap; }
	.pd-btn:hover { color: var(--t); border-color: var(--tm); text-decoration: none; }
	.pd-btn.active { background: var(--bg2); color: var(--t); }
	.pd-btn--accent:hover { background: var(--ac); color: var(--bg); border-color: var(--ac-text, var(--accent-text)); }

	/* GRID */
	.pd-grid { display: flex; flex-direction: column; gap: 1.75rem; }
	.pd-row--pace { display: grid; grid-template-columns: 2fr 1fr; gap: 2px; }
	.pd-row--split { display: grid; grid-template-columns: 1fr 1fr; gap: 2px; }

	/* SECTIONS */
	.pd-sec { position: relative; }
	/* "Show" bridge pulse from Key Moments */
	.pd :global(.pd-flash) { animation: -global-pd-flash-pulse 1.6s ease; }
	@keyframes -global-pd-flash-pulse {
		0% { box-shadow: 0 0 0 2px rgba(226,75,74,0); }
		25% { box-shadow: 0 0 0 2px rgba(226,75,74,.65); }
		100% { box-shadow: 0 0 0 2px rgba(226,75,74,0); }
	}
	@media (prefers-reduced-motion: reduce) { .pd :global(.pd-flash) { animation: none; } }
	.pd-sec__minitoggle { position: absolute; top: 4px; right: 4px; z-index: 5; background: var(--bg); border: 1px solid rgba(46,50,64,.5); cursor: pointer; padding: 3px 5px; line-height: 1; opacity: .4; transition: opacity .15s; }
	.pd-sec__minitoggle:hover { opacity: 1; }
	.pd-chev { display: inline-block; font-size: 9.5px; color: var(--tm); transition: transform .2s; }
	.pd-chev.rotated { transform: rotate(-90deg); }
	.pd-sec__body { max-height: 2000px; opacity: 1; overflow: visible; transition: max-height .35s ease, opacity .25s ease; }
	.pd-sec__body.collapsed { max-height: 0; opacity: 0; overflow: hidden; }

	/* FOOTER */
	.pd-footer { margin-top: 3rem; padding: 1.25rem 0; border-top: 1px solid rgba(46,50,64,.5); }
	.pd-footer__row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: .5rem; }
	.pd-footer__legal { margin-top: .7rem; font-family: var(--fm); font-size: 9.5px; line-height: 1.6; color: var(--tm); opacity: .6; }
	.pd-footer__stats { display: flex; gap: 2rem; }
	.pd-footer__label { font-family: var(--fm); font-size: 9px; color: var(--tm); text-transform: uppercase; letter-spacing: .1em; margin-bottom: 1px; }
	.pd-footer__val { font-family: var(--fm); font-size: 10px; }
	.pd-footer__val--accent { color: var(--ac-text, var(--accent-text)); }
	.pd-footer__copy { font-family: var(--fm); font-size: 9.5px; color: var(--tm); opacity: .4; text-transform: uppercase; letter-spacing: .1em; }

	/* LOADING */
	.pd-loading { display: flex; align-items: center; justify-content: center; padding: 3rem; font-family: var(--fm); color: var(--tm); }

	/* RESPONSIVE */
	@media (max-width: 1100px) { .pd-overview { grid-template-columns: repeat(2, 1fr); } .pd-row--pace, .pd-row--split { grid-template-columns: 1fr; } }
	@media (max-width: 900px) {
		.pd-sb { position: fixed; top: 52px; left: 0; bottom: 0; width: var(--sbw); min-width: var(--sbw); transform: translateX(-100%); transition: transform .25s ease; }
		.pd-sb:not(.collapsed) { transform: translateX(0); }
		.collapsed .pd-sb__full { opacity: 1; pointer-events: auto; }
		.collapsed .pd-sb__mini { display: none; }
		.pd-sb__toggle { display: none; }
		.pd-nav__burger { display: flex; }
		.pd-main { padding: 1rem; }
		.pd-overview { grid-template-columns: 1fr 1fr; }
		.pd-toolbar { flex-direction: column; }
	}
	@media (max-width: 480px) {
		.pd-overview { grid-template-columns: 1fr; }
		.pd-header__title { font-size: 20px; }
		.pd-main { padding: .75rem; }
	}

	.pd-sec { position: relative; }

	.pd-ov-card { transition: border-color .2s; }


	.pd-row--split, .pd-row--pace { gap: 3px; }


	.pd-sec--split { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
	.pd-uc { background: var(--bg-secondary); border: 1px solid var(--border); padding: 16px 18px; height: 100%; box-sizing: border-box; }
	.pd-uc__title { display: inline-block; font-family: var(--font-heading); font-size: 10px; font-weight: 900; font-style: italic; color: #fff; background: var(--accent); text-transform: uppercase; letter-spacing: .07em; padding: 3px 10px; margin-bottom: 12px; }
	.pd-uc__row { display: grid; grid-template-columns: 34px 40px 78px 40px 1fr; align-items: center; gap: 6px; font-family: var(--fm); font-size: 12px; padding: 5px 0; }
	.pd-uc__lap { color: var(--text-muted); font-size: 10px; }
	.pd-uc__w, .pd-uc__l { font-family: var(--font-heading); font-weight: 800; font-size: 12px; letter-spacing: .04em; }
	.pd-uc__vs { color: var(--text-muted); font-size: 10px; text-transform: uppercase; letter-spacing: .05em; text-align: center; }
	.pd-uc__gain { text-align: right; font-weight: 700; color: var(--timing-pb); font-variant-numeric: tabular-nums; }
</style>
