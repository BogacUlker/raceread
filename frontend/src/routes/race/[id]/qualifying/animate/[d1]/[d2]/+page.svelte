<!--
	Animated Qualifying Comparison - two drivers' qualifying laps
	animated simultaneously on track map, showing real-time gap.
	Time-based animation with playback controls and live gap chart.
-->
<script>
	import { onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n/index.js';
	import { TEAM_COLORS } from '$lib/constants.js';
	import { formatLapTime } from '$lib/utils/format.js';

	let { data } = $props();

	let raceId = $derived(data.raceId);
	let raceInfo = $derived(data.raceInfo);
	let d1 = $derived(data.d1);
	let d2 = $derived(data.d2);
	let qualData = $derived(data.qualifyingTelemetry);
	let circuitData = $derived(data.circuit);

	// Extract driver data
	let driver1Data = $derived(qualData?.drivers?.find(d => d.driver === d1) || null);
	let driver2Data = $derived(qualData?.drivers?.find(d => d.driver === d2) || null);
	let hasData = $derived(driver1Data?.samples?.length > 0 && driver2Data?.samples?.length > 0);

	let team1 = $derived(driver1Data?.team || '');
	let team2 = $derived(driver2Data?.team || '');
	let color1 = $derived(TEAM_COLORS[team1] || '#00D7B6');
	let color2 = $derived(TEAM_COLORS[team2] || '#E24B4A');

	let samples1 = $derived(driver1Data?.samples || []);
	let samples2 = $derived(driver2Data?.samples || []);
	let lapTime1 = $derived(driver1Data?.lap_time_s || 0);
	let lapTime2 = $derived(driver2Data?.lap_time_s || 0);
	let session1 = $derived(driver1Data?.session || 'Q3');
	let session2 = $derived(driver2Data?.session || 'Q3');

	let totalTime = $derived(Math.max(lapTime1, lapTime2));
	let fasterDriver = $derived(lapTime1 <= lapTime2 ? d1 : d2);

	// Container for responsive sizing
	let containerEl = $state(null);
	let containerWidth = $state(800);

	$effect(() => {
		if (!containerEl) return;
		const ro = new ResizeObserver(entries => {
			for (const entry of entries) {
				containerWidth = entry.contentRect.width;
			}
		});
		ro.observe(containerEl);
		return () => ro.disconnect();
	});

	// Animation state
	let playing = $state(false);
	let progress = $state(0);
	let speed = $state(1);
	let animFrame = $state(null);
	let lastTimestamp = $state(null);

	// Driver finished states
	let d1Finished = $derived(totalTime > 0 && progress * totalTime >= lapTime1);
	let d2Finished = $derived(totalTime > 0 && progress * totalTime >= lapTime2);

	const SPEED_OPTIONS = [0.25, 0.5, 1, 2, 4];

	function animate(timestamp) {
		if (!lastTimestamp) lastTimestamp = timestamp;
		const dt = (timestamp - lastTimestamp) / 1000;
		lastTimestamp = timestamp;

		if (totalTime > 0) {
			progress = Math.min(1, progress + (dt * speed) / totalTime);
		}

		if (progress >= 1) {
			playing = false;
			lastTimestamp = null;
			return;
		}

		animFrame = requestAnimationFrame(animate);
	}

	function togglePlay() {
		playing = !playing;
		if (playing) {
			if (progress >= 1) progress = 0;
			lastTimestamp = null;
			animFrame = requestAnimationFrame(animate);
		} else {
			if (animFrame) cancelAnimationFrame(animFrame);
			lastTimestamp = null;
		}
	}

	function resetAnimation() {
		playing = false;
		if (animFrame) cancelAnimationFrame(animFrame);
		progress = 0;
		lastTimestamp = null;
	}

	let scrubbing = $state(false);
	let scrubEl = $state(null);

	function seekTo(e) {
		if (!scrubEl) return;
		const rect = scrubEl.getBoundingClientRect();
		const x = (e.clientX || e.touches?.[0]?.clientX || 0) - rect.left;
		progress = Math.max(0, Math.min(1, x / rect.width));
	}

	function startScrub(e) {
		scrubbing = true;
		seekTo(e);
		// Pause playback while scrubbing
		if (playing) {
			playing = false;
			if (animFrame) cancelAnimationFrame(animFrame);
			lastTimestamp = null;
		}
		window.addEventListener('mousemove', onScrubMove);
		window.addEventListener('mouseup', stopScrub);
		window.addEventListener('touchmove', onScrubMove);
		window.addEventListener('touchend', stopScrub);
	}

	function onScrubMove(e) {
		if (!scrubbing) return;
		e.preventDefault();
		seekTo(e);
	}

	function stopScrub() {
		scrubbing = false;
		if (typeof window !== 'undefined') {
			window.removeEventListener('mousemove', onScrubMove);
			window.removeEventListener('mouseup', stopScrub);
			window.removeEventListener('touchmove', onScrubMove);
			window.removeEventListener('touchend', stopScrub);
		}
	}

	// Clean up on destroy
	onDestroy(() => {
		if (animFrame) cancelAnimationFrame(animFrame);
		stopScrub();
	});

	// Also clean up via $effect for hot reloads
	$effect(() => {
		return () => {
			if (animFrame) cancelAnimationFrame(animFrame);
		};
	});

	// ----- Interpolation -----

	function getPositionAtTime(samples, time) {
		if (!samples.length) return { x: 0, y: 0, speed: 0, dist: 0 };

		// Clamp to last sample if past end
		const lastSample = samples[samples.length - 1];
		if (time >= lastSample.time_s) {
			return { x: lastSample.x, y: lastSample.y, speed: lastSample.speed, dist: lastSample.dist };
		}

		const firstSample = samples[0];
		if (time <= firstSample.time_s) {
			return { x: firstSample.x, y: firstSample.y, speed: firstSample.speed, dist: firstSample.dist };
		}

		// Binary search
		let lo = 0;
		let hi = samples.length - 1;
		while (lo < hi - 1) {
			const mid = (lo + hi) >> 1;
			if (samples[mid].time_s <= time) lo = mid;
			else hi = mid;
		}

		const a = samples[lo];
		const b = samples[hi];
		if (a.time_s === b.time_s) return { x: a.x, y: a.y, speed: a.speed, dist: a.dist };

		const frac = (time - a.time_s) / (b.time_s - a.time_s);
		return {
			x: a.x + (b.x - a.x) * frac,
			y: a.y + (b.y - a.y) * frac,
			speed: a.speed + (b.speed - a.speed) * frac,
			dist: a.dist + (b.dist - a.dist) * frac,
		};
	}

	function getDistAtTime(samples, time) {
		if (!samples.length) return 0;
		const lastSample = samples[samples.length - 1];
		if (time >= lastSample.time_s) return lastSample.dist;
		const firstSample = samples[0];
		if (time <= firstSample.time_s) return firstSample.dist;

		let lo = 0;
		let hi = samples.length - 1;
		while (lo < hi - 1) {
			const mid = (lo + hi) >> 1;
			if (samples[mid].time_s <= time) lo = mid;
			else hi = mid;
		}
		const a = samples[lo];
		const b = samples[hi];
		if (a.time_s === b.time_s) return a.dist;
		const frac = (time - a.time_s) / (b.time_s - a.time_s);
		return a.dist + (b.dist - a.dist) * frac;
	}

	function getTimeAtDist(samples, dist) {
		if (!samples.length) return 0;
		const lastSample = samples[samples.length - 1];
		if (dist >= lastSample.dist) return lastSample.time_s;
		const firstSample = samples[0];
		if (dist <= firstSample.dist) return firstSample.time_s;

		let lo = 0;
		let hi = samples.length - 1;
		while (lo < hi - 1) {
			const mid = (lo + hi) >> 1;
			if (samples[mid].dist <= dist) lo = mid;
			else hi = mid;
		}
		const a = samples[lo];
		const b = samples[hi];
		if (a.dist === b.dist) return a.time_s;
		const frac = (dist - a.dist) / (b.dist - a.dist);
		return a.time_s + (b.time_s - a.time_s) * frac;
	}

	// ----- Current positions -----

	let currentTime = $derived(progress * totalTime);

	let pos1 = $derived(getPositionAtTime(samples1, Math.min(currentTime, lapTime1)));
	let pos2 = $derived(getPositionAtTime(samples2, Math.min(currentTime, lapTime2)));

	// ----- Gap calculation -----
	// Use x,y position matching to compute gap correctly
	// (raw dist values are not comparable between drivers due to different racing lines)
	let currentGap = $derived.by(() => {
		if (!gapPoints.length || totalTime === 0) return 0;

		const t1 = Math.min(currentTime, lapTime1);
		const dist1 = getDistAtTime(samples1, t1);

		// Interpolate gap from precomputed x,y-matched curve
		if (gapPoints.length < 2) return gapPoints[0]?.gap || 0;

		let lo = 0, hi = gapPoints.length - 1;
		while (lo < hi - 1) {
			const mid = (lo + hi) >> 1;
			if (gapPoints[mid].dist <= dist1) lo = mid;
			else hi = mid;
		}
		const a = gapPoints[lo];
		const b = gapPoints[hi];
		if (a.dist === b.dist) return a.gap;
		const frac = (dist1 - a.dist) / (b.dist - a.dist);
		return a.gap + (b.gap - a.gap) * frac;
	});

	function formatGapDisplay(gap) {
		if (gap == null || isNaN(gap)) return '0.000s';
		const sign = gap >= 0 ? '+' : '-';
		return `${sign}${Math.abs(gap).toFixed(3)}s`;
	}

	let gapLeader = $derived(currentGap >= 0 ? d1 : d2);

	// ----- Track outline -----

	let outlinePoints = $derived.by(() => {
		if (circuitData?.outline?.length > 0) return circuitData.outline;
		// Fallback: use driver 1 samples as outline
		return samples1.map(s => ({ x: s.x, y: s.y }));
	});

	let corners = $derived(circuitData?.corners || []);
	let trackLength = $derived(circuitData?.track_length || (samples1.length > 0 ? samples1[samples1.length - 1].dist : 0));

	// ----- SVG bounds -----

	let bounds = $derived.by(() => {
		const allPoints = [...outlinePoints];
		if (samples1.length) allPoints.push(...samples1.map(s => ({ x: s.x, y: s.y })));
		if (samples2.length) allPoints.push(...samples2.map(s => ({ x: s.x, y: s.y })));

		if (!allPoints.length) return { minX: 0, maxX: 1, minY: 0, maxY: 1 };

		let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
		for (const p of allPoints) {
			if (p.x != null && p.y != null) {
				minX = Math.min(minX, p.x);
				maxX = Math.max(maxX, p.x);
				minY = Math.min(minY, p.y);
				maxY = Math.max(maxY, p.y);
			}
		}

		const padX = (maxX - minX) * 0.04;
		const padY = (maxY - minY) * 0.04;
		return { minX: minX - padX, maxX: maxX + padX, minY: minY - padY, maxY: maxY + padY };
	});

	let svgWidth = $derived(Math.max(300, containerWidth));
	let svgHeight = $derived.by(() => {
		const rangeX = bounds.maxX - bounds.minX;
		const rangeY = bounds.maxY - bounds.minY;
		if (rangeX === 0) return 400;
		const aspect = rangeY / rangeX;
		return Math.max(300, Math.min(600, svgWidth * aspect));
	});

	let viewBox = $derived(`${bounds.minX} ${bounds.minY} ${bounds.maxX - bounds.minX} ${bounds.maxY - bounds.minY}`);

	// Coordinate transform: SVG uses data coords directly via viewBox.
	// Y is flipped because SVG y goes down, but track y goes up.
	// We handle this by flipping in the viewBox or transform.
	let flipY = $derived.by(() => {
		// Check if y-axis needs flipping (track coords have y increasing upward)
		if (outlinePoints.length < 2) return false;
		return true; // Generally F1 track coords have y going up
	});

	// Build outline path
	let outlinePath = $derived.by(() => {
		if (!outlinePoints.length) return '';
		return outlinePoints
			.filter(p => p.x != null && p.y != null)
			.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${flipY ? -p.y : p.y}`)
			.join(' ') + ' Z';
	});

	// Transform a point for SVG
	function tx(x) { return x; }
	function ty(y) { return flipY ? -y : y; }

	// Recompute viewBox with flipped y
	let viewBoxFlipped = $derived.by(() => {
		const allPoints = [...outlinePoints];
		if (samples1.length) allPoints.push(...samples1.map(s => ({ x: s.x, y: s.y })));
		if (samples2.length) allPoints.push(...samples2.map(s => ({ x: s.x, y: s.y })));

		if (!allPoints.length) return '0 0 1 1';

		let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
		for (const p of allPoints) {
			if (p.x != null && p.y != null) {
				const px = tx(p.x);
				const py = ty(p.y);
				minX = Math.min(minX, px);
				maxX = Math.max(maxX, px);
				minY = Math.min(minY, py);
				maxY = Math.max(maxY, py);
			}
		}

		const padX = (maxX - minX) * 0.04;
		const padY = (maxY - minY) * 0.04;
		return `${minX - padX} ${minY - padY} ${maxX - minX + 2 * padX} ${maxY - minY + 2 * padY}`;
	});

	// Scale factor for consistent stroke/circle sizes in viewBox coords
	let scaleFactor = $derived.by(() => {
		const rangeX = bounds.maxX - bounds.minX;
		if (rangeX === 0) return 1;
		return rangeX / svgWidth;
	});

	let dotRadius = $derived(Math.max(8, 22 * scaleFactor));
	let trackStroke = $derived(Math.max(6, 24 * scaleFactor));
	let labelOffset = $derived(Math.max(12, 28 * scaleFactor));
	let fontSize = $derived(Math.max(10, 20 * scaleFactor));
	let cornerFontSize = $derived(Math.max(5, 10 * scaleFactor));

	// ----- Gap chart data (draws progressively) -----

	let gapChartW = $derived(Math.max(300, containerWidth));
	const gapChartH = 140;
	const gapM = { top: 32, right: 20, bottom: 30, left: 50 };

	// Pre-compute gap by projecting each d1 position onto d2's path segments.
	// Raw dist values differ between drivers (different racing lines),
	// so we use x,y segment projection for accurate time interpolation.
	let gapPoints = $derived.by(() => {
		if (!samples1.length || !samples2.length) return [];

		const ratio = samples2.length / samples1.length;
		const totalGap = lapTime2 - lapTime1;

		// For each d1 sample, project its (x,y) onto d2's path segments
		const raw = samples1.map((s1, i) => {
			const center = Math.round(i * ratio);
			const lo = Math.max(0, center - 25);
			const hi = Math.min(samples2.length - 2, center + 25);

			let bestDistSq = Infinity;
			let bestTime = samples2[Math.min(center, samples2.length - 1)].time_s;

			for (let j = lo; j <= hi; j++) {
				const ax = samples2[j].x, ay = samples2[j].y;
				const bx = samples2[j + 1].x, by = samples2[j + 1].y;

				// Project s1 onto segment [a, b]
				const abx = bx - ax, aby = by - ay;
				const apx = s1.x - ax, apy = s1.y - ay;
				const ab2 = abx * abx + aby * aby;
				const t = ab2 > 0 ? Math.max(0, Math.min(1, (apx * abx + apy * aby) / ab2)) : 0;

				const px = ax + t * abx, py = ay + t * aby;
				const dx = s1.x - px, dy = s1.y - py;
				const dSq = dx * dx + dy * dy;

				if (dSq < bestDistSq) {
					bestDistSq = dSq;
					bestTime = samples2[j].time_s + t * (samples2[j + 1].time_s - samples2[j].time_s);
				}
			}

			return { dist: s1.dist, gap: bestTime - s1.time_s };
		});

		// Force known endpoints (start=0, end=exact total gap)
		raw[0].gap = 0;
		raw[raw.length - 1].gap = totalGap;

		// Smooth with 5-point moving average to reduce residual noise
		return raw.map((p, i) => {
			if (i < 2 || i >= raw.length - 2) return p;
			const avg = (raw[i - 2].gap + raw[i - 1].gap + p.gap + raw[i + 1].gap + raw[i + 2].gap) / 5;
			return { dist: p.dist, gap: avg };
		});
	});

	let maxAbsGap = $derived.by(() => {
		if (!gapPoints.length) return 0.5;
		const m = Math.max(0.05, ...gapPoints.map(p => Math.abs(p.gap)));
		return m * 1.2;
	});

	// Current distance for progressive draw (use d1's dist since gap curve is indexed by it)
	let currentMaxDist = $derived.by(() => {
		if (!samples1.length) return 0;
		const t1 = Math.min(currentTime, lapTime1);
		return getDistAtTime(samples1, t1);
	});

	let visibleGapPoints = $derived(gapPoints.filter(p => p.dist <= currentMaxDist));

	function gapX(dist) {
		const inner = gapChartW - gapM.left - gapM.right;
		return gapM.left + (dist / trackLength) * inner;
	}

	function gapY(gap) {
		const inner = gapChartH - gapM.top - gapM.bottom;
		return gapM.top + ((maxAbsGap - gap) / (2 * maxAbsGap)) * inner;
	}

	// Build SVG path for visible gap points with color segments
	let gapLinePath = $derived.by(() => {
		if (visibleGapPoints.length < 2) return '';
		return visibleGapPoints
			.map((p, i) => `${i === 0 ? 'M' : 'L'}${gapX(p.dist).toFixed(1)},${gapY(p.gap).toFixed(1)}`)
			.join(' ');
	});

	// Split gap line into segments by leader for coloring
	let gapSegments = $derived.by(() => {
		if (visibleGapPoints.length < 2) return [];

		const segments = [];
		let currentSegment = { color: visibleGapPoints[0].gap >= 0 ? color1 : color2, points: [visibleGapPoints[0]] };

		for (let i = 1; i < visibleGapPoints.length; i++) {
			const p = visibleGapPoints[i];
			const segColor = p.gap >= 0 ? color1 : color2;

			if (segColor !== currentSegment.color) {
				// Find zero crossing for smooth transition
				const prev = visibleGapPoints[i - 1];
				if (prev.gap !== p.gap) {
					const frac = Math.abs(prev.gap) / (Math.abs(prev.gap) + Math.abs(p.gap));
					const zeroDist = prev.dist + (p.dist - prev.dist) * frac;
					currentSegment.points.push({ dist: zeroDist, gap: 0 });
				}
				segments.push(currentSegment);
				currentSegment = { color: segColor, points: [{ dist: currentSegment.points.at(-1).dist, gap: 0 }] };
			}
			currentSegment.points.push(p);
		}
		segments.push(currentSegment);

		return segments;
	});

	// Gap chart axis labels
	let gapTicks = $derived.by(() => {
		const ticks = [];
		const step = maxAbsGap > 0.5 ? 0.5 : maxAbsGap > 0.2 ? 0.2 : 0.1;
		for (let v = -maxAbsGap; v <= maxAbsGap; v += step) {
			if (Math.abs(v) < 0.001) v = 0;
			ticks.push(v);
		}
		return ticks;
	});

	let distTicks = $derived.by(() => {
		if (trackLength === 0) return [];
		const ticks = [];
		const step = trackLength > 4000 ? 1000 : 500;
		for (let d = 0; d <= trackLength; d += step) {
			ticks.push(d);
		}
		return ticks;
	});
</script>

<svelte:head>
	<title>{d1} vs {d2} {$t('qualifying.animate_title')} - {raceInfo?.name || ''} - RaceRead</title>
	<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" />
</svelte:head>

<section class="qanim" bind:this={containerEl}>
	{#if !hasData}
		<div class="qanim__no-data">
			<a href="/race/{raceId}" class="qanim__back">&larr; {raceInfo?.name}</a>
			<p>{$t('qualifying.animate_no_data')}</p>
		</div>
	{:else}
		<!-- Top bar: back + title + controls -->
		<div class="qanim__topbar">
			<a href="/race/{raceId}" class="qanim__back">&larr; {raceInfo?.name}</a>
			<div class="qanim__title-group">
				<span class="qanim__badge" style="background:{color1}">{d1}</span>
				<span class="qanim__vs">{$t('charts.vs')}</span>
				<span class="qanim__badge" style="background:{color2}">{d2}</span>
			</div>
			<div class="qanim__ctrl-group">
				<button class="qanim__btn qanim__btn--play" onclick={togglePlay}>
					{#if playing}
						<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><rect x="6" y="4" width="4" height="16" /><rect x="14" y="4" width="4" height="16" /></svg>
					{:else}
						<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><polygon points="5,3 19,12 5,21" /></svg>
					{/if}
				</button>
				{#each SPEED_OPTIONS as s}
					<button class="qanim__speed-btn" class:qanim__speed-btn--active={speed === s} onclick={() => speed = s}>{s}x</button>
				{/each}
				<button class="qanim__btn qanim__btn--reset" onclick={resetAnimation}>
					<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1,4 1,10 7,10" /><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" /></svg>
				</button>
			</div>
		</div>

		<!-- 3-column layout: D1 stats | Track Map | D2 stats -->
		<div class="qanim__arena">
			<!-- Left panel: Driver 1 -->
			<div class="qanim__panel qanim__panel--left">
				<div class="qanim__p-badge" style="background:{color1}">{d1}</div>
				<p class="qanim__p-team">{team1}</p>
				<p class="qanim__p-session">{session1}</p>

				<div class="qanim__p-stat qanim__p-stat--big">
					<span class="qanim__p-stat-label">{$t('qualifying.current_speed')}</span>
					<span class="qanim__p-stat-value" style="color:{color1}">{d1Finished ? '-' : Math.round(pos1.speed)}</span>
					<span class="qanim__p-stat-unit">km/h</span>
				</div>

				<div class="qanim__p-stat">
					<span class="qanim__p-stat-label">{$t('qualifying.lap_time')}</span>
					<span class="qanim__p-stat-value">{formatLapTime(lapTime1)}</span>
				</div>

				{#if d1Finished}
					<div class="qanim__p-finished">{$t('qualifying.finished')}</div>
				{/if}
			</div>

			<!-- Center: Track map -->
			<div class="qanim__map">
				<svg viewBox={viewBoxFlipped} class="qanim__track-svg" preserveAspectRatio="xMidYMid meet">
					<!-- Glow filters for driver dots -->
					<defs>
						<filter id="glow1" x="-50%" y="-50%" width="200%" height="200%">
							<feGaussianBlur stdDeviation="3" result="blur" />
							<feFlood flood-color={color1} flood-opacity="0.5" result="color" />
							<feComposite in="color" in2="blur" operator="in" result="glow" />
							<feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
						</filter>
						<filter id="glow2" x="-50%" y="-50%" width="200%" height="200%">
							<feGaussianBlur stdDeviation="3" result="blur" />
							<feFlood flood-color={color2} flood-opacity="0.5" result="color" />
							<feComposite in="color" in2="blur" operator="in" result="glow" />
							<feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
						</filter>
					</defs>
					{#if outlinePath}
						<path d={outlinePath} fill="none" stroke="var(--border)" stroke-width={trackStroke} stroke-linecap="round" stroke-linejoin="round" opacity="0.55" />
					{/if}
					{#each corners as corner}
						<text x={tx(corner.x)} y={ty(corner.y) - cornerFontSize * 1.2} fill="var(--text-muted)" font-size={cornerFontSize} font-family="var(--font-mono)" text-anchor="middle" opacity="0.5">{corner.number}</text>
					{/each}
					<circle cx={tx(pos1.x)} cy={ty(pos1.y)} r={dotRadius} fill={color1} stroke="#000" stroke-width={dotRadius * 0.15} opacity={d1Finished ? 0.4 : 1} filter={d1Finished ? "none" : "url(#glow1)"} />
					<text x={tx(pos1.x)} y={ty(pos1.y) - labelOffset} fill={color1} font-size={fontSize} font-family="var(--font-mono)" font-weight="700" text-anchor="middle" opacity={d1Finished ? 0.4 : 1}>{d1}</text>
					<circle cx={tx(pos2.x)} cy={ty(pos2.y)} r={dotRadius} fill={color2} stroke="#000" stroke-width={dotRadius * 0.15} opacity={d2Finished ? 0.4 : 1} filter={d2Finished ? "none" : "url(#glow2)"} />
					<text x={tx(pos2.x)} y={ty(pos2.y) + labelOffset + fontSize} fill={color2} font-size={fontSize} font-family="var(--font-mono)" font-weight="700" text-anchor="middle" opacity={d2Finished ? 0.4 : 1}>{d2}</text>
				</svg>

				<!-- Gap overlay centered -->
				<div class="qanim__gap-overlay">
					<span class="qanim__gap-value" style="color:{currentGap >= 0 ? color1 : color2}">{formatGapDisplay(currentGap)}</span>
					<span class="qanim__gap-leader">{gapLeader} {$t('qualifying.leads')}</span>
				</div>
			</div>

			<!-- Right panel: Driver 2 -->
			<div class="qanim__panel qanim__panel--right">
				<div class="qanim__p-badge" style="background:{color2}">{d2}</div>
				<p class="qanim__p-team">{team2}</p>
				<p class="qanim__p-session">{session2}</p>

				<div class="qanim__p-stat qanim__p-stat--big">
					<span class="qanim__p-stat-label">{$t('qualifying.current_speed')}</span>
					<span class="qanim__p-stat-value" style="color:{color2}">{d2Finished ? '-' : Math.round(pos2.speed)}</span>
					<span class="qanim__p-stat-unit">km/h</span>
				</div>

				<div class="qanim__p-stat">
					<span class="qanim__p-stat-label">{$t('qualifying.lap_time')}</span>
					<span class="qanim__p-stat-value">{formatLapTime(lapTime2)}</span>
				</div>

				{#if d2Finished}
					<div class="qanim__p-finished">{$t('qualifying.finished')}</div>
				{/if}
			</div>
		</div>

		<!-- Bottom: scrub bar + mini gap chart -->
		<div class="qanim__bottom">
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div class="qanim__scrub" bind:this={scrubEl} onmousedown={startScrub} ontouchstart={startScrub} role="slider" tabindex="0" aria-valuenow={Math.round(progress * 100)} aria-valuemin="0" aria-valuemax="100">
				<div class="qanim__scrub-track">
					<div class="qanim__scrub-fill" style="width:{progress * 100}%"></div>
					<div class="qanim__scrub-thumb" style="left:{progress * 100}%"></div>
				</div>
				<div class="qanim__scrub-labels">
					<span>{formatLapTime(currentTime)}</span>
					<span>{formatLapTime(totalTime)}</span>
				</div>
			</div>

			<!-- Mini gap chart -->
			<div class="qanim__gap-label">
				<span class="qanim__gap-label-text">{$t('qualifying.gap_chart_title')}</span>
				<span class="qanim__gap-label-drivers"><span style="color:{color1}">{d1}</span> vs <span style="color:{color2}">{d2}</span></span>
			</div>
			<svg viewBox="0 0 {gapChartW} 80" class="qanim__gap-mini" preserveAspectRatio="none">
				<line x1={gapM.left} y1={40} x2={gapChartW - gapM.right} y2={40} stroke="var(--border)" stroke-opacity="0.3" />
				{#each gapSegments as seg}
					{#if seg.points.length >= 2}
						<polyline points={seg.points.map(p => `${gapX(p.dist).toFixed(1)},${(40 - (p.gap / maxAbsGap) * 36).toFixed(1)}`).join(' ')} fill="none" stroke={seg.color} stroke-width="1.5" stroke-linecap="round" />
					{/if}
				{/each}
			</svg>
		</div>
	{/if}
</section>
<style>
	.qanim {
		position: fixed; inset: 0; z-index: 200;
		background: #0F1117; color: #E8E8ED;
		font-family: 'DM Sans', sans-serif;
		-webkit-font-smoothing: antialiased;
		display: flex; flex-direction: column;
		overflow: hidden;
		--fm: 'JetBrains Mono', monospace;
		--fh: 'Space Grotesk', sans-serif;
		--ac: #E24B4A;
		--bg2: #1A1D27;
		--brd: #2E3240;
		--tm: #6B7280;
	}

	/* Top bar */
	.qanim__topbar {
		display: flex; align-items: center; justify-content: space-between;
		padding: 0.6rem 1.5rem;
		border-bottom: 1px solid rgba(46,50,64,.5);
		flex-shrink: 0;
	}
	.qanim__back { font-family: var(--fm); font-size: 10px; color: var(--ac); text-decoration: none; text-transform: uppercase; letter-spacing: .08em; }
	.qanim__back:hover { text-decoration: none; opacity: .8; }
	.qanim__title-group { display: flex; align-items: center; gap: .5rem; }
	.qanim__badge { font-family: var(--fm); font-size: 13px; font-weight: 700; padding: 3px 10px; color: #000; }
	.qanim__vs { font-family: var(--fm); font-size: 11px; color: var(--tm); }
	.qanim__ctrl-group { display: flex; align-items: center; gap: 4px; }
	.qanim__btn { background: var(--bg2); border: 1px solid var(--brd); color: #E8E8ED; cursor: pointer; display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; transition: all .15s; }
	.qanim__btn:hover { border-color: var(--ac); }
	.qanim__speed-btn { font-family: var(--fm); font-size: 10px; padding: 4px 8px; background: none; border: 1px solid var(--brd); color: var(--tm); cursor: pointer; }
	.qanim__speed-btn--active { background: var(--ac); color: #fff; border-color: var(--ac); }

	/* 3-column arena */
	.qanim__arena { flex: 1; display: flex; min-height: 0; }

	/* Side panels */
	.qanim__panel { width: 180px; flex-shrink: 0; background: var(--bg2); padding: 1.25rem; display: flex; flex-direction: column; align-items: center; gap: .75rem; border-top: 1px solid rgba(46,50,64,.3); }
	.qanim__panel--left { border-right: 1px solid rgba(46,50,64,.3); }
	.qanim__panel--right { border-left: 1px solid rgba(46,50,64,.3); }
	.qanim__p-badge { font-family: var(--fh); font-size: 22px; font-weight: 700; padding: 6px 20px; color: #000; }
	.qanim__p-team { font-size: 13px; color: #9CA3AF; font-weight: 500; }
	.qanim__p-session { font-family: var(--fm); font-size: 11px; color: #9CA3AF; text-transform: uppercase; letter-spacing: .1em; }
	.qanim__p-stat { text-align: center; margin-top: .5rem; }
	.qanim__p-stat--big { margin-top: auto; }
	.qanim__p-stat-label { display: block; font-family: var(--fm); font-size: 10px; color: #9CA3AF; text-transform: uppercase; letter-spacing: .1em; margin-bottom: 5px; }
	.qanim__p-stat-value { font-family: var(--fh); font-size: 38px; font-weight: 700; line-height: 1; }
	.qanim__p-stat--big .qanim__p-stat-value { font-size: 54px; }
	.qanim__p-stat-unit { display: block; font-family: var(--fm); font-size: 11px; color: #9CA3AF; margin-top: 3px; }
	.qanim__p-finished { font-family: var(--fm); font-size: 12px; color: #22C55E; text-transform: uppercase; letter-spacing: .12em; margin-top: auto; font-weight: 700; }

	/* Center map */
	.qanim__map { flex: 1; position: relative; display: flex; align-items: center; justify-content: center; overflow: hidden; }
	.qanim__track-svg { width: 100%; height: 100%; }
	.qanim__gap-overlay { position: absolute; top: 1rem; right: 1rem; background: rgba(15,17,23,.85); padding: .6rem 1rem; text-align: center; border: 1px solid rgba(46,50,64,.4); }
	.qanim__gap-value { font-family: var(--fh); font-size: 22px; font-weight: 700; display: block; }
	.qanim__gap-leader { font-family: var(--fm); font-size: 9px; color: var(--tm); text-transform: uppercase; letter-spacing: .08em; }

	/* Bottom bar */
	.qanim__bottom { flex-shrink: 0; padding: .5rem 1.5rem .75rem; background: var(--bg2); border-top: 1px solid rgba(46,50,64,.4); }
	.qanim__scrub { cursor: pointer; margin-bottom: .25rem; padding: 6px 0; touch-action: none; user-select: none; }
	.qanim__scrub-track { position: relative; height: 5px; background: var(--brd); }
	.qanim__scrub-fill { position: absolute; top: 0; left: 0; height: 100%; background: var(--ac); }
	.qanim__scrub-thumb { position: absolute; top: 50%; transform: translate(-50%, -50%); width: 14px; height: 14px; background: #E8E8ED; transition: transform .1s; }
	.qanim__scrub:active .qanim__scrub-thumb { transform: translate(-50%, -50%) scale(1.3); }
	.qanim__scrub-labels { display: flex; justify-content: space-between; font-family: var(--fm); font-size: 9px; color: var(--tm); margin-top: 3px; }
	.qanim__gap-label { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px; }
	.qanim__gap-label-text { font-family: var(--fm); font-size: 9px; color: var(--tm); text-transform: uppercase; letter-spacing: .1em; }
	.qanim__gap-label-drivers { font-family: var(--fm); font-size: 9px; }
	.qanim__gap-mini { width: 100%; height: 50px; }

	/* No data */
	.qanim__no-data { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1rem; font-family: var(--fm); color: var(--tm); }

	/* Responsive */
	@media (max-width: 900px) {
		.qanim__panel { width: 120px; padding: .75rem; }
		.qanim__p-stat--big .qanim__p-stat-value { font-size: 32px; }
		.qanim__p-badge { font-size: 16px; }
	}
	@media (max-width: 640px) {
		.qanim__panel { display: none; }
		.qanim__topbar { padding: .5rem .75rem; flex-wrap: wrap; gap: .5rem; }
	}
</style>