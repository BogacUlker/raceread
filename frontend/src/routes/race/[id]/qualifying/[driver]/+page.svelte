<script>
	import { t, locale } from '$lib/i18n/index.js';
	import { TEAM_COLORS, COMPOUND_COLORS } from '$lib/constants.js';
	import { formatLapTime } from '$lib/utils/format.js';

	let { data } = $props();
	let raceId = $derived(data.raceId);
	let raceInfo = $derived(data.raceInfo);
	let driverCode = $derived(data.driverCode);
	let races = $derived(data.races || []);

	let driverData = $derived.by(() => (data.qualifying?.drivers || []).find(d => d.driver === driverCode) || null);
	let teamColor = $derived(TEAM_COLORS[driverData?.team] || '#888');
	let otherDrivers = $derived((data.qualifying?.drivers || []).filter(d => d.driver !== driverCode).sort((a, b) => (a.position ?? 99) - (b.position ?? 99)));
	let compareTarget = $state('');
	let circuit = $derived(data.circuit);

	// Track outline for sector map
	let trackOutline = $derived.by(() => {
		if (!circuit?.outline?.length) return '';
		const pts = circuit.outline;
		const xs = pts.map(p => p.x), ys = pts.map(p => p.y);
		const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
		const w = maxX - minX || 1, h = maxY - minY || 1;
		return pts.map((p, i) => {
			const nx = ((p.x - minX) / w) * 400 + 50;
			const ny = (1 - (p.y - minY) / h) * 350 + 25;
			return (i === 0 ? 'M' : 'L') + nx.toFixed(1) + ',' + ny.toFixed(1);
		}).join(' ') + ' Z';
	});

	// Corner positions for track map
	let cornerPositions = $derived.by(() => {
		if (!circuit?.corners?.length || !circuit?.outline?.length) return [];
		const pts = circuit.outline;
		const xs = pts.map(p => p.x), ys = pts.map(p => p.y);
		const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
		const w = maxX - minX || 1, h = maxY - minY || 1;
		return circuit.corners.map(c => ({
			number: c.number,
			x: ((c.x - minX) / w) * 400 + 50,
			y: (1 - (c.y - minY) / h) * 350 + 25,
			dist: c.distance,
		}));
	});

	// Split track outline into 3 sector paths by cumulative distance
	let sectorPaths = $derived.by(() => {
		if (!circuit?.outline?.length || !bestSectors?.s1 || !bestSectors?.s2 || !bestSectors?.s3) return null;
		const pts = circuit.outline;
		const tl = circuit.track_length || 5235;

		// Compute cumulative distance along outline
		const cumDist = [0];
		for (let i = 1; i < pts.length; i++) {
			const dx = pts[i].x - pts[i-1].x;
			const dy = pts[i].y - pts[i-1].y;
			cumDist.push(cumDist[i-1] + Math.sqrt(dx*dx + dy*dy));
		}
		const totalDist = cumDist[cumDist.length - 1];

		// Sector boundaries as fraction of total outline distance
		// Use time ratio as approximation (best we can do without exact sector boundary data)
		const total = bestSectors.s1.value + bestSectors.s2.value + bestSectors.s3.value;
		const s1Frac = bestSectors.s1.value / total;
		const s2Frac = (bestSectors.s1.value + bestSectors.s2.value) / total;
		const s1Dist = totalDist * s1Frac;
		const s2Dist = totalDist * s2Frac;

		// Find point indices at sector boundaries
		let s1Idx = 0, s2Idx = 0;
		for (let i = 0; i < cumDist.length; i++) {
			if (cumDist[i] <= s1Dist) s1Idx = i;
			if (cumDist[i] <= s2Dist) s2Idx = i;
		}

		const xs = pts.map(p => p.x), ys = pts.map(p => p.y);
		const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
		const w = maxX - minX || 1, h = maxY - minY || 1;

		function toPath(slice) {
			return slice.map((p, i) => {
				const nx = ((p.x - minX) / w) * 400 + 50;
				const ny = (1 - (p.y - minY) / h) * 350 + 25;
				return (i === 0 ? 'M' : 'L') + nx.toFixed(1) + ',' + ny.toFixed(1);
			}).join(' ');
		}

		return {
			s1: toPath(pts.slice(0, s1Idx + 1)),
			s2: toPath(pts.slice(s1Idx, s2Idx + 1)),
			s3: toPath(pts.slice(s2Idx).concat([pts[0]])),
		};
	});
	let attempts = $derived(driverData?.attempts || []);
	let hasAttempts = $derived(attempts.length > 0);

	let attemptsBySession = $derived.by(() => {
		const g = { Q1: [], Q2: [], Q3: [] };
		for (const a of attempts) { if (g[a.session]) g[a.session].push(a); }
		return g;
	});
	let activeSessions = $derived(['Q1', 'Q2', 'Q3'].filter(s => attemptsBySession[s].length > 0));

	let bestSectors = $derived.by(() => {
		const valid = attempts.filter(a => !a.is_deleted && a.time_s != null);
		if (!valid.length) return null;
		let b1 = { value: Infinity, attempt: null }, b2 = { value: Infinity, attempt: null }, b3 = { value: Infinity, attempt: null };
		for (const a of valid) {
			if (a.s1 != null && a.s1 < b1.value) b1 = { value: a.s1, attempt: a };
			if (a.s2 != null && a.s2 < b2.value) b2 = { value: a.s2, attempt: a };
			if (a.s3 != null && a.s3 < b3.value) b3 = { value: a.s3, attempt: a };
		}
		return { s1: b1.attempt ? b1 : null, s2: b2.attempt ? b2 : null, s3: b3.attempt ? b3 : null };
	});
	let theoreticalBest = $derived.by(() => {
		if (!bestSectors?.s1 || !bestSectors?.s2 || !bestSectors?.s3) return null;
		return bestSectors.s1.value + bestSectors.s2.value + bestSectors.s3.value;
	});

	let chartAttempts = $derived(attempts.filter(a => !a.is_deleted && a.time_s != null));
	const chartW = 1000, chartH = 300;
	const margin = { top: 28, right: 28, bottom: 44, left: 68 };
	const innerW = chartW - margin.left - margin.right, innerH = chartH - margin.top - margin.bottom;

	let timeRange = $derived.by(() => {
		if (!chartAttempts.length) return { min: 0, max: 1 };
		const times = chartAttempts.map(a => a.time_s);
		const mn = Math.min(...times), mx = Math.max(...times), pad = (mx - mn) * 0.15 || 0.5;
		return { min: mn - pad, max: mx + pad };
	});
	function xScale(i) { return chartAttempts.length <= 1 ? margin.left + innerW / 2 : margin.left + (i / (chartAttempts.length - 1)) * innerW; }
	function yScale(t) { const { min, max } = timeRange; return max === min ? margin.top + innerH / 2 : margin.top + ((t - min) / (max - min)) * innerH; }
	let sessionSeparators = $derived.by(() => { const s = []; let prev = null; for (let i = 0; i < chartAttempts.length; i++) { if (prev && chartAttempts[i].session !== prev) s.push({ x: (xScale(i-1)+xScale(i))/2, label: chartAttempts[i].session }); prev = chartAttempts[i].session; } return s; });
	let linePath = $derived.by(() => chartAttempts.length === 0 ? '' : chartAttempts.map((a,i) => `${i===0?'M':'L'} ${xScale(i).toFixed(1)} ${yScale(a.time_s).toFixed(1)}`).join(' '));
	function labelYOffset(i) { const c = chartAttempts[i].time_s, p = i>0?chartAttempts[i-1].time_s:null, n = i<chartAttempts.length-1?chartAttempts[i+1].time_s:null; if(!p&&n!=null) return c<=n?-14:22; if(!n&&p!=null) return c<=p?-14:22; if(!p&&!n) return -14; return (c>p&&c>n)?22:-14; }
	function textOnColor(h) { if(!h||h.length<7) return '#fff'; const r=parseInt(h.slice(1,3),16),g=parseInt(h.slice(3,5),16),b=parseInt(h.slice(5,7),16); return (0.299*r+0.587*g+0.114*b)/255>0.5?'#000':'#fff'; }
	function compoundColor(c) { return COMPOUND_COLORS[c] || '#888'; }
	function isBestSector(a, s) { if(!bestSectors) return false; const b=bestSectors[s]; return b?.attempt?.attempt_number===a.attempt_number && b?.attempt?.session===a.session; }
	function tc(driver) { const d = (data.qualifying?.drivers||[]).find(x => x.driver === driver); return TEAM_COLORS[d?.team] || '#6B7280'; }

	// Sidebar
	
	// Uppercase race name with proper GRAND PRIX (not PRİX)
	function gpName(name) {
		if (!name) return '';
		const parts = name.split('Grand Prix');
		if (parts.length === 2) return parts[0].toUpperCase() + 'GRAND PRIX';
		return name.toUpperCase();
	}

	let sidebarCollapsed = $state(true);
</script>

<svelte:head>
	<title>{driverCode} {$t('qualifying.title')} - {raceInfo.name} - RaceRead</title>
	<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" />
</svelte:head>

<div class="pq">
	<!-- NAV -->
	<nav class="pq-nav">
		<div class="pq-nav__inner">
			<a href="/" class="pq-nav__logo">RACEREAD</a>
			<button class="pq-nav__lang" onclick={() => locale.set($locale === 'en' ? 'tr' : 'en')}>{$locale === 'en' ? 'TR' : 'EN'}</button>
		</div>
	</nav>

	<div class="pq-layout">
		<!-- SIDEBAR -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<aside class="pq-sb" class:collapsed={sidebarCollapsed}
			onmouseenter={() => { clearTimeout(window.__sbTimer); sidebarCollapsed = false; }}
			onmouseleave={() => { window.__sbTimer = setTimeout(() => { sidebarCollapsed = true; }, 300); }}>
			<button class="pq-sb__toggle" onclick={() => sidebarCollapsed = !sidebarCollapsed}>
				<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d={sidebarCollapsed ? 'M6 3l5 5-5 5' : 'M10 3L5 8l5 5'} stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
			</button>
			<div class="pq-sb__full">
				<div class="pq-sb__sec"><nav class="pq-sb__nav">
					{#each races as race, i}
						<a href="/race/{race.id}" class="pq-sb__race"><span class="pq-sb__rc">R{i+1}</span><span class="pq-sb__rn">{race.circuit}</span></a>
					{/each}
				</nav></div>
				<div class="pq-sb__bottom"><a href="/race/{raceId}" class="pq-sb__home">&larr; {gpName(raceInfo.name)}</a></div>
			</div>
			<div class="pq-sb__mini">
				{#each races as race, i}<a href="/race/{race.id}" class="pq-sb__mr" style="border-left-color:{tc(race.winner)}">R{i+1}</a>{/each}
			</div>
		</aside>

		<!-- MAIN -->
		<div class="pq-main">
			<a href="/race/{raceId}" class="pq-back">&larr; {gpName(raceInfo.name)}</a>

			{#if !driverData}
				<div class="pq-empty">{$t('common.no_data')}</div>
			{:else}
				<!-- Driver Header -->
				<div class="pq-header">
					<div class="pq-header__left">
						<span class="pq-header__badge" style="background:{teamColor}; color:{textOnColor(teamColor)}">{driverCode}</span>
						<div class="pq-header__info">
							<span class="pq-header__team">{driverData.team}</span>
							<span class="pq-header__pos">P{driverData.position}{#if driverData.gap_to_pole === 0} - {$t('qualifying.pole')}{:else if driverData.gap_to_pole != null} - +{driverData.gap_to_pole.toFixed(3)}s{/if}</span>
						</div>
					</div>

				</div>


				<!-- Overview Cards -->
				<div class="pq-overview">
					<div class="pq-ov pq-ov--accent">
						<p class="pq-ov__label">{$locale === 'tr' ? 'En İyi Tur' : 'Best Lap'}</p>
						<h3 class="pq-ov__value">{driverData.q3 || driverData.q2 || driverData.q1 || '-'}</h3>
						<p class="pq-ov__sub">{driverData.q3 ? 'Q3' : driverData.q2 ? 'Q2' : 'Q1'}</p>
					</div>
					<div class="pq-ov">
						<p class="pq-ov__label">{$locale === 'tr' ? 'Pole Farkı' : 'Gap to Pole'}</p>
						<h3 class="pq-ov__value">{driverData.gap_to_pole === 0 ? 'POLE' : driverData.gap_to_pole != null ? '+' + driverData.gap_to_pole.toFixed(3) + 's' : '-'}</h3>
						<p class="pq-ov__sub">P{driverData.position}</p>
					</div>
					<div class="pq-ov">
						<p class="pq-ov__label">{$locale === 'tr' ? 'Deneme Sayısı' : 'Attempts'}</p>
						<h3 class="pq-ov__value">{attempts.length}</h3>
						<p class="pq-ov__sub">{activeSessions.join(' + ')}</p>
					</div>
					{#if theoreticalBest}
						{@const actual = driverData.q3_s || driverData.q2_s || driverData.q1_s}
						<div class="pq-ov">
							<p class="pq-ov__label">{$locale === 'tr' ? 'Teorik En İyi' : 'Theoretical Best'}</p>
							<h3 class="pq-ov__value">{formatLapTime(theoreticalBest)}</h3>
							{#if actual}<p class="pq-ov__sub pq-ov__sub--delta">+{(actual - theoreticalBest).toFixed(3)}s</p>{/if}
						</div>
					{/if}
				</div>

				<!-- Q1→Q2→Q3 Phase Progression -->
				{#if activeSessions.length > 0}
				<div class="pq-phase">
					<h3 class="pq-phase__title">{$locale === 'tr' ? 'Sıralama Aşamaları' : 'Qualifying Phases'}</h3>
					<div class="pq-phase__timeline">
						{#each ['Q1', 'Q2', 'Q3'] as session}
							{@const sessionAttempts = attemptsBySession[session] || []}
							{@const isActive = sessionAttempts.length > 0}
							{@const bestInSession = sessionAttempts.filter(a => !a.is_deleted && a.time_s).sort((a,b) => a.time_s - b.time_s)[0]}
							{@const hasDeleted = sessionAttempts.some(a => a.is_deleted)}
							<div class="pq-phase__session" class:pq-phase__session--active={isActive} class:pq-phase__session--inactive={!isActive}>
								<div class="pq-phase__label">{session}</div>
								{#if isActive && bestInSession}
									<div class="pq-phase__time">{formatLapTime(bestInSession.time_s)}</div>
									<div class="pq-phase__attempts">
										{#each sessionAttempts as a}
											<span class="pq-phase__dot" class:pq-phase__dot--best={a.is_personal_best && !a.is_deleted} class:pq-phase__dot--deleted={a.is_deleted} class:pq-phase__dot--normal={!a.is_personal_best && !a.is_deleted} title="{formatLapTime(a.time_s)}{a.is_deleted ? ' (deleted)' : ''}"></span>
										{/each}
									</div>
									{#if hasDeleted}<span class="pq-phase__deleted-tag">{$locale === 'tr' ? 'silinen tur' : 'deleted'}</span>{/if}
								{:else}
									<div class="pq-phase__na">{$locale === 'tr' ? 'geçemedi' : 'eliminated'}</div>
								{/if}
							</div>
							{#if session !== 'Q3'}
								<div class="pq-phase__arrow" class:pq-phase__arrow--active={attemptsBySession[session === 'Q1' ? 'Q2' : 'Q3']?.length > 0}>→</div>
							{/if}
						{/each}
					</div>
				</div>
				{/if}

				<!-- Sector Track Map -->
				{#if trackOutline && bestSectors?.s1}
				<div class="pq-trackmap">
					<h3 class="pq-trackmap__title">{$locale === 'tr' ? 'Sektör Haritası' : 'Sector Map'}</h3>
					<div class="pq-trackmap__wrap">
						<svg viewBox="0 0 500 400" class="pq-trackmap__svg" preserveAspectRatio="xMidYMid meet">
							<!-- Full track outline dim -->
							<path d={trackOutline} fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="14" stroke-linejoin="round" stroke-linecap="round" />

							{#if sectorPaths}
								<path d={sectorPaths.s1} fill="none" stroke="#E24B4A" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" opacity="0.85" />
								<path d={sectorPaths.s2} fill="none" stroke="#3B82F6" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" opacity="0.85" />
								<path d={sectorPaths.s3} fill="none" stroke="#22C55E" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" opacity="0.85" />
							{/if}

							<!-- Corner labels -->
							{#each cornerPositions as c}
								<text x={c.x} y={c.y - 12} fill="rgba(255,255,255,0.5)" font-size="10" font-family="'JetBrains Mono'" text-anchor="middle">{c.number}</text>
							{/each}

							<!-- S/F marker at track start point -->
							{#if circuit?.outline?.length}
								{@const pts = circuit.outline}
								{@const xs = pts.map(p => p.x)}
								{@const ys = pts.map(p => p.y)}
								{@const minX = Math.min(...xs)}
								{@const maxX = Math.max(...xs)}
								{@const minY = Math.min(...ys)}
								{@const maxY = Math.max(...ys)}
								{@const w = maxX - minX || 1}
								{@const h = maxY - minY || 1}
								{@const sfX = ((pts[0].x - minX) / w) * 400 + 50}
								{@const sfY = (1 - (pts[0].y - minY) / h) * 350 + 25}
								<circle cx={sfX} cy={sfY} r="5" fill="none" stroke="#E24B4A" stroke-width="2" />
								<text x={sfX} y={sfY + 16} fill="#E24B4A" font-size="9" font-family="'JetBrains Mono'" text-anchor="middle">S/F</text>
							{/if}
						</svg>

						<!-- Sector legend with times -->
						<div class="pq-trackmap__legend">
							<div class="pq-trackmap__sec" style="border-left-color: #E24B4A">
								<span class="pq-trackmap__sec-label">S1</span>
								<span class="pq-trackmap__sec-time">{bestSectors.s1.value.toFixed(3)}s</span>
								<span class="pq-trackmap__sec-src">{bestSectors.s1.attempt.session}</span>
							</div>
							<div class="pq-trackmap__sec" style="border-left-color: #3B82F6">
								<span class="pq-trackmap__sec-label">S2</span>
								<span class="pq-trackmap__sec-time">{bestSectors.s2.value.toFixed(3)}s</span>
								<span class="pq-trackmap__sec-src">{bestSectors.s2.attempt.session}</span>
							</div>
							<div class="pq-trackmap__sec" style="border-left-color: #22C55E">
								<span class="pq-trackmap__sec-label">S3</span>
								<span class="pq-trackmap__sec-time">{bestSectors.s3.value.toFixed(3)}s</span>
								<span class="pq-trackmap__sec-src">{bestSectors.s3.attempt.session}</span>
							</div>
						</div>
					</div>
				</div>
				{/if}

				{#if !hasAttempts}
					<div class="chart-card"><div class="chart-card__header"><span class="chart-card__title">{$t('qualifying_detail.attempts')}</span></div><p class="pq-no-data">{$t('qualifying_detail.no_attempts')}</p></div>
				{:else}
					<!-- Attempts Table -->
					<div class="chart-card">
						<div class="chart-card__header"><span class="chart-card__title">{$t('qualifying_detail.attempts')}</span></div>
						<div class="pq-table-wrap">
							<table class="pq-table">
								<thead><tr>
									<th>{$t('qualifying_detail.session_col')}</th><th>#</th><th class="r">{$t('qualifying_detail.time')}</th><th class="r">S1</th><th class="r">S2</th><th class="r">S3</th><th>{$t('common.compound')}</th><th class="c">{$t('qualifying_detail.status')}</th>
								</tr></thead>
								<tbody>
									{#each activeSessions as session}
										{#each attemptsBySession[session] as attempt, idx}
											{@const isDel = attempt.is_deleted}
											{@const isPB = attempt.is_personal_best}
											<tr class:row--del={isDel} class:row--pb={isPB && !isDel}>
												<td>{#if idx === 0}<span class="pq-session">{session}</span>{/if}</td>
												<td class="c muted">{attempt.attempt_number}</td>
												<td class="r" class:strike={isDel}>{attempt.time_str || formatLapTime(attempt.time_s)}</td>
												<td class="r" class:strike={isDel} class:best={!isDel && isBestSector(attempt,'s1')}>{attempt.s1 != null ? attempt.s1.toFixed(3) : '-'}</td>
												<td class="r" class:strike={isDel} class:best={!isDel && isBestSector(attempt,'s2')}>{attempt.s2 != null ? attempt.s2.toFixed(3) : '-'}</td>
												<td class="r" class:strike={isDel} class:best={!isDel && isBestSector(attempt,'s3')}>{attempt.s3 != null ? attempt.s3.toFixed(3) : '-'}</td>
												<td>{#if attempt.compound}<span class="pq-compound" style="background:{compoundColor(attempt.compound)}"></span> <span class="muted">{attempt.compound}</span>{:else}-{/if}</td>
												<td class="c">{#if isDel}<span class="st-del">{$t('qualifying_detail.deleted')}</span>{:else if isPB}<span class="st-pb">PB</span>{:else}<span class="muted">-</span>{/if}</td>
											</tr>
										{/each}
									{/each}
								</tbody>
							</table>
						</div>
					</div>

					<!-- Improvement Chart -->
					{#if chartAttempts.length > 1}
						<div class="chart-card">
							<div class="chart-card__header"><span class="chart-card__title">{$t('qualifying_detail.improvement')}</span></div>
							<svg viewBox="0 0 {chartW} {chartH}" class="pq-chart">
								{#each Array(5) as _, i}{@const tv = timeRange.min + ((timeRange.max - timeRange.min) / 4) * i}{@const ty = yScale(tv)}
									<line x1={margin.left} y1={ty} x2={chartW - margin.right} y2={ty} stroke="#2E3240" stroke-opacity="0.5" />
									<text x={margin.left - 8} y={ty + 4} fill="#6B7280" font-size="10" text-anchor="end" font-family="'JetBrains Mono'">{formatLapTime(tv)}</text>
								{/each}
								{#each sessionSeparators as sep}<line x1={sep.x} y1={margin.top} x2={sep.x} y2={chartH - margin.bottom} stroke="#6B7280" stroke-opacity="0.3" stroke-dasharray="4 3" /><text x={sep.x} y={chartH - margin.bottom + 16} fill="#6B7280" font-size="10" text-anchor="middle" font-family="'JetBrains Mono'">{sep.label}</text>{/each}
								{#if chartAttempts.length > 0}<text x={xScale(0)} y={chartH - margin.bottom + 16} fill="#6B7280" font-size="10" text-anchor="middle" font-family="'JetBrains Mono'">{chartAttempts[0].session}</text>{/if}
								<path d={linePath} fill="none" stroke={teamColor} stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" />
								{#each chartAttempts as a, i}
									<circle cx={xScale(i)} cy={yScale(a.time_s)} r={a.is_personal_best ? 6 : 4.5} fill={a.is_personal_best ? '#22C55E' : teamColor} stroke="#0F1117" stroke-width="1.5" />
									<text x={xScale(i)} y={yScale(a.time_s) + labelYOffset(i)} fill="#9CA3AF" font-size="10" text-anchor="middle" font-family="'JetBrains Mono'">{formatLapTime(a.time_s)}</text>
								{/each}
							</svg>
						</div>
					{/if}

					<!-- Best Sectors -->
					{#if bestSectors?.s1 && bestSectors?.s2 && bestSectors?.s3}
						<div class="chart-card">
							<div class="chart-card__header"><span class="chart-card__title">{$t('qualifying_detail.best_sectors')}</span></div>
							<div class="pq-sectors">
								{#each [['S1', bestSectors.s1], ['S2', bestSectors.s2], ['S3', bestSectors.s3]] as [label, d]}
									<div class="pq-sector"><span class="pq-sector__label">{label}</span><span class="pq-sector__time">{d.value.toFixed(3)}s</span><span class="pq-sector__src">{d.attempt.session} #{d.attempt.attempt_number}</span></div>
								{/each}
								{#if theoreticalBest}{@const actual = driverData.q3_s || driverData.q2_s || driverData.q1_s}
									<div class="pq-sector pq-sector--total"><span class="pq-sector__label">{$t('qualifying.theoretical_best')}</span><span class="pq-sector__time">{formatLapTime(theoreticalBest)}</span>{#if actual}<span class="pq-sector__delta">+{(actual - theoreticalBest).toFixed(3)}s</span>{/if}</div>
								{/if}
							</div>
						</div>
					{/if}

					<!-- Animate Compare -->
					{#if otherDrivers.length > 0}
						<div class="chart-card">
							<div class="chart-card__header"><span class="chart-card__title">{$t('qualifying.animate_title')}</span></div>
							<div class="pq-compare">
								<span class="pq-compare__label">{driverCode} {$t('charts.vs')}</span>
								<select class="pq-compare__select" bind:value={compareTarget}>
									<option value="">{$t('charts.select_drivers')}</option>
									{#each otherDrivers as d}<option value={d.driver}>P{d.position} - {d.driver} ({d.team})</option>{/each}
								</select>
								{#if compareTarget}<a href="/race/{raceId}/qualifying/animate/{driverCode.toLowerCase()}/{compareTarget.toLowerCase()}" class="pq-compare__btn">{$t('qualifying.play')} ▶</a>{/if}
							</div>
						</div>
					{/if}
				{/if}
			{/if}
		</div>
	</div>
</div>

<style>
	.pq {
		--bg: #0F1117; --bg2: #1A1D27; --bgc: #22252F; --t: #E8E8ED; --t2: #9CA3AF; --tm: #6B7280; --brd: #2E3240; --ac: #E24B4A;
		--fh: 'Space Grotesk', sans-serif; --fb: 'DM Sans', sans-serif; --fm: 'JetBrains Mono', monospace;
		--sbw: 200px; --sbc: 44px;
		position: fixed; inset: 0; z-index: 200; overflow: hidden; background: var(--bg); color: var(--t); font-family: var(--fb); -webkit-font-smoothing: antialiased;
	}
	.pq :global(*) { border-radius: 0 !important; }
	.pq :global(.chart-card) { border-radius: 0 !important; border: none !important; background: var(--bg2) !important; border-left: 2px solid transparent !important; transition: border-color .25s, box-shadow .25s !important; }
	.pq :global(.chart-card:hover) { border-left-color: var(--ac) !important; box-shadow: -4px 0 20px -4px rgba(226,75,74,.12) !important; }
	.pq :global(.chart-card__title) { font-family: var(--fh) !important; text-transform: uppercase; letter-spacing: .03em; }

	/* NAV */
	.pq-nav { position: relative; z-index: 60; background: var(--bg); border-bottom: 1px solid rgba(46,50,64,.6); }
	.pq-nav__inner { padding: 0 1.25rem; height: 52px; display: flex; align-items: center; justify-content: space-between; }
	.pq-nav__logo { font-family: var(--fh); font-weight: 700; font-size: 16px; letter-spacing: -.03em; color: var(--t); text-decoration: none; }
	.pq-nav__logo:hover { text-decoration: none; }
	.pq-nav__lang { font-family: var(--fm); font-size: 10px; font-weight: 700; letter-spacing: .1em; color: var(--ac); background: none; border: 1px solid var(--brd); padding: 4px 10px; cursor: pointer; }

	/* LAYOUT */
	.pq-layout { display: flex; height: calc(100vh - 52px); }

	/* SIDEBAR (same pattern) */
	.pq-sb { width: var(--sbw); min-width: var(--sbw); background: var(--bg2); border-right: 1px solid rgba(46,50,64,.5); display: flex; flex-direction: column; position: relative; z-index: 55; overflow: hidden; transition: width .25s ease, min-width .25s ease; }
	.pq-sb.collapsed { width: var(--sbc); min-width: var(--sbc); }
	.pq-sb__toggle { position: absolute; top: 10px; right: 6px; z-index: 5; width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; background: var(--bg2); border: 1px solid rgba(46,50,64,.5); color: var(--tm); cursor: pointer; transition: all .2s; }
	.pq-sb__toggle:hover { color: var(--t); }
	.collapsed .pq-sb__toggle { right: auto; left: 50%; transform: translateX(-50%); }
	.pq-sb__full { display: flex; flex-direction: column; flex: 1; overflow-y: auto; white-space: nowrap; opacity: 1; transition: opacity .2s ease .1s; }
	.collapsed .pq-sb__full { opacity: 0; pointer-events: none; transition: opacity .15s ease 0s; }
	.pq-sb__mini { display: flex; flex-direction: column; align-items: center; gap: 4px; padding-top: 44px; position: absolute; top: 0; left: 0; right: 0; bottom: 0; opacity: 0; pointer-events: none; transition: opacity .15s ease 0s; }
	.collapsed .pq-sb__mini { opacity: 1; pointer-events: auto; transition: opacity .2s ease .15s; }
	.pq-sb__sec { padding: 1rem; }
	.pq-sb__nav { display: flex; flex-direction: column; gap: 1px; }
	.pq-sb__race { display: flex; align-items: center; gap: .4rem; padding: .4rem .5rem; text-decoration: none; color: inherit; font-family: var(--fm); font-size: 11px; transition: background .15s; }
	.pq-sb__race:hover { background: rgba(226,75,74,.08); text-decoration: none; }
	.pq-sb__rc { font-size: 10px; color: var(--ac); min-width: 22px; }
	.pq-sb__rn { flex: 1; }
	.pq-sb__bottom { margin-top: auto; padding: 1rem; border-top: 1px solid rgba(46,50,64,.4); }
	.pq-sb__home { font-family: var(--fm); font-size: 10px; color: var(--ac); text-decoration: none; text-transform: uppercase; letter-spacing: .08em; }
	.pq-sb__home:hover { text-decoration: none; opacity: .8; }
	.pq-sb__mr { font-family: var(--fm); font-size: 9px; font-weight: 700; color: var(--t2); text-decoration: none; padding: 3px 0; border-left: 2px solid transparent; padding-left: 6px; width: 34px; text-align: center; }
	.pq-sb__mr:hover { color: var(--ac); text-decoration: none; }

	/* MAIN */
	.pq-main { flex: 1; overflow-y: auto; padding: 1.5rem 2rem 3rem; display: flex; flex-direction: column; gap: 1.5rem; }

	/* Back */
	.pq-back { font-family: var(--fm); font-size: 11px; color: var(--ac); text-decoration: none; letter-spacing: .08em; }
	.pq-back:hover { text-decoration: none; opacity: .8; }

	/* Header */
	.pq-header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }
	.pq-header__left { display: flex; align-items: center; gap: 1rem; }
	.pq-header__badge { font-family: var(--fh); font-size: 24px; font-weight: 700; padding: 6px 18px; letter-spacing: .04em; }
	.pq-header__info { display: flex; flex-direction: column; gap: 2px; }
	.pq-header__team { font-size: 14px; color: var(--t2); }
	.pq-header__pos { font-family: var(--fm); font-size: 13px; color: var(--tm); }
	.pq-header__right { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
	.pq-header__best-label { font-family: var(--fm); font-size: 9px; color: var(--tm); text-transform: uppercase; letter-spacing: .08em; }
	.pq-header__best-val { font-family: var(--fh); font-size: 26px; font-weight: 700; font-variant-numeric: tabular-nums; }

	
	/* Overview Cards */
	.pq-overview { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 2px; }
	.pq-ov { background: var(--bg2); padding: 1.2rem 1.4rem; border-left: 3px solid var(--brd); transition: border-color .2s; }
	.pq-ov:hover { border-left-color: var(--ac); }
	.pq-ov--accent { border-left-color: var(--ac); background: linear-gradient(135deg, var(--bg2) 0%, rgba(226,75,74,.06) 100%); }
	.pq-ov__label { font-family: var(--fm); font-size: 9px; color: var(--tm); text-transform: uppercase; letter-spacing: .12em; margin-bottom: .5rem; }
	.pq-ov__value { font-family: var(--fh); font-size: 26px; font-weight: 700; line-height: 1; letter-spacing: -.02em; }
	.pq-ov--accent .pq-ov__value { color: var(--ac); }
	.pq-ov__sub { font-family: var(--fm); font-size: 9px; color: var(--tm); margin-top: 4px; text-transform: uppercase; letter-spacing: .04em; }
	.pq-ov__sub--delta { color: #F59E0B; }

	/* Empty */
	.pq-empty, .pq-no-data { font-family: var(--fm); font-size: 13px; color: var(--tm); padding: 2rem; text-align: center; }

	/* Table */
	.pq-table-wrap { overflow-x: auto; }
	.pq-table { width: 100%; border-collapse: collapse; }
	.pq-table th, .pq-table td { font-family: var(--fm); font-size: 12px; padding: 6px 10px; white-space: nowrap; }
	.pq-table th { font-size: 10px; font-weight: 600; color: var(--tm); text-transform: uppercase; letter-spacing: .04em; padding-bottom: 8px; border-bottom: 1px solid var(--brd); }
	.pq-table td { border-bottom: 1px solid rgba(255,255,255,.04); font-variant-numeric: tabular-nums; }
	.r { text-align: right; }
	.c { text-align: center; }
	.muted { color: var(--tm); }
	.pq-session { font-weight: 700; font-size: 11px; color: var(--t2); background: var(--bgc); padding: 2px 6px; }
	.row--del td { background: rgba(239,68,68,.06); color: var(--tm); }
	.row--pb td { background: rgba(34,197,94,.06); }
	.strike { text-decoration: line-through; opacity: .5; }
	.best { color: #22C55E; font-weight: 700; }
	.pq-compound { display: inline-block; width: 8px; height: 8px; border-radius: 50% !important; flex-shrink: 0; }
	.st-del { font-size: 9px; font-weight: 600; color: #EF4444; text-transform: uppercase; }
	.st-pb { font-size: 9px; font-weight: 700; color: #22C55E; }

	/* Chart */
	.pq-chart { width: 100%; max-height: 280px; }

	/* Sectors */
	.pq-sectors { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 1rem; padding: .5rem 0; }
	.pq-sector { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 1rem; background: var(--bgc); border-left: 2px solid var(--brd); }
	.pq-sector--total { border-left-color: #22C55E; background: rgba(34,197,94,.04); }
	.pq-sector__label { font-family: var(--fm); font-size: 11px; font-weight: 600; color: var(--tm); text-transform: uppercase; }
	.pq-sector__time { font-family: var(--fh); font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; }
	.pq-sector__src { font-family: var(--fm); font-size: 10px; color: var(--tm); }
	.pq-sector__delta { font-family: var(--fm); font-size: 10px; color: #F59E0B; }

	/* Compare */
	.pq-compare { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; padding: .5rem 0; }
	.pq-compare__label { font-family: var(--fm); font-size: 13px; font-weight: 600; color: var(--t2); }
	.pq-compare__select { font-family: var(--fm); font-size: 12px; padding: 5px 8px; background: var(--bg); color: var(--t); border: 1px solid var(--brd); min-width: 180px; }
	.pq-compare__btn { font-family: var(--fm); font-size: 12px; font-weight: 600; padding: 5px 14px; background: var(--ac); color: #fff; border: none; text-decoration: none; }
	.pq-compare__btn:hover { opacity: .85; text-decoration: none; }

	/* Responsive */
	@media (max-width: 900px) {
		.pq-sb { position: fixed; top: 52px; left: 0; bottom: 0; transform: translateX(-100%); transition: transform .25s ease; }
		.pq-sb:not(.collapsed) { transform: translateX(0); }
		.collapsed .pq-sb__full { opacity: 1; pointer-events: auto; }
		.collapsed .pq-sb__mini { display: none; }
		.pq-sb__toggle { display: none; }
	}
	@media (max-width: 768px) { .pq-header { flex-direction: column; align-items: flex-start; } .pq-header__right { align-items: flex-start; } .pq-sectors { grid-template-columns: repeat(2, 1fr); } .pq-main { padding: 1rem; } }
	@media (max-width: 480px) { .pq-header__badge { font-size: 18px; padding: 4px 12px; } .pq-header__best-val { font-size: 18px; } .pq-sectors { grid-template-columns: 1fr; } }

	/* Phase Progression */
	.pq-phase { margin-bottom: 1.5rem; }
	.pq-phase__title { font-family: var(--fh); font-size: 15px; font-weight: 700; text-transform: uppercase; margin-bottom: 1rem; border-left: 3px solid var(--ac); padding-left: .75rem; }
	.pq-phase__timeline { display: flex; align-items: center; gap: .5rem; }
	.pq-phase__session { background: var(--bg2); padding: 1.25rem 1.5rem; flex: 1; text-align: center; border-top: 3px solid var(--brd); transition: border-color .2s; }
	.pq-phase__session--active { border-top-color: var(--ac); }
	.pq-phase__session--inactive { opacity: .3; }
	.pq-phase__label { font-family: var(--fh); font-size: 18px; font-weight: 700; margin-bottom: .5rem; }
	.pq-phase__time { font-family: var(--fm); font-size: 16px; font-weight: 700; color: var(--ac); }
	.pq-phase__attempts { display: flex; justify-content: center; gap: 4px; margin-top: .5rem; }
	.pq-phase__dot { width: 8px; height: 8px; }
	.pq-phase__dot--best { background: #22C55E; }
	.pq-phase__dot--deleted { background: #EF4444; }
	.pq-phase__dot--normal { background: #6B7280; }
	.pq-phase__deleted-tag { font-family: var(--fm); font-size: 9px; color: #EF4444; text-transform: uppercase; display: block; margin-top: .25rem; }
	.pq-phase__na { font-family: var(--fm); font-size: 11px; color: var(--tm); text-transform: uppercase; margin-top: .5rem; }
	.pq-phase__arrow { font-size: 20px; color: var(--brd); }
	.pq-phase__arrow--active { color: var(--ac); }

	/* Sector Track Map */
	.pq-trackmap { margin-bottom: 1.5rem; }
	.pq-trackmap__title { font-family: var(--fh); font-size: 15px; font-weight: 700; text-transform: uppercase; margin-bottom: 1rem; border-left: 3px solid var(--ac); padding-left: .75rem; }
	.pq-trackmap__wrap { display: grid; grid-template-columns: 1fr auto; gap: 1.5rem; background: var(--bg2); padding: 1.5rem; }
	.pq-trackmap__svg { width: 100%; max-height: 350px; }
	.pq-trackmap__legend { display: flex; flex-direction: column; gap: .5rem; justify-content: center; }
	.pq-trackmap__sec { padding: .75rem 1rem; border-left: 3px solid; background: rgba(15,17,23,.5); }
	.pq-trackmap__sec-label { font-family: var(--fh); font-size: 16px; font-weight: 700; display: block; margin-bottom: 2px; }
	.pq-trackmap__sec-time { font-family: var(--fm); font-size: 14px; font-weight: 700; display: block; }
	.pq-trackmap__sec-src { font-family: var(--fm); font-size: 10px; color: var(--tm); }

	@media (max-width: 640px) {
		.pq-phase__timeline { flex-direction: column; }
		.pq-phase__arrow { transform: rotate(90deg); }
		.pq-trackmap__wrap { grid-template-columns: 1fr; }
	}
</style>
