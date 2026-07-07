<!--
	Key Moments - 3-4 cards derived from the verified annotations.
	Each card's "show" button deep-links into the right chart: selects the
	driver, pins it on the pace chart, scrolls to the section and flashes it.
-->
<script>
	import { goto, replaceState } from '$app/navigation';
	import { t, locale } from '$lib/i18n/index.js';
	import RadioCard from '$lib/components/ui/RadioCard.svelte';
	import { selectedDrivers, pinnedDriver, momentFocus } from '$lib/stores/race.js';

	let { annotations = [], raceId = '', radio = [], teamsMap = {} } = $props();

	function clipFor(m) {
		// nearest clip from the moment's driver within 3 laps (radio calls
		// naturally arrive a couple of laps around the event)
		let best = null;
		for (const c of radio) {
			if (c.driver !== m.driver || c.lap == null) continue;
			const d = Math.abs(c.lap - m.lap);
			if (d <= 3 && (best === null || d < Math.abs(best.lap - m.lap))) best = c;
		}
		return best;
	}

	const SECTION_BY_TYPE = {
		pace: 'pace',
		strategy: 'strategy',
		pit: 'pit-stops',
		energy: 'energy-timeline',
		delta: 'energy',
		speed_trace: 'speed-trace',
		track: 'track-map',
		traffic: 'traffic',
	};
	const RANK = { high: 0, medium: 1, low: 2 };

	let moments = $derived.by(() => {
		const eligible = annotations.filter(
			(a) => a.driver && a.lap && SECTION_BY_TYPE[a.chart_type] && (a.text_en || a.text_tr)
		);
		const sorted = [...eligible].sort(
			(a, b) => (RANK[a.severity] ?? 3) - (RANK[b.severity] ?? 3)
		);
		const picked = [];
		const seenTypes = new Set();
		for (const a of sorted) {
			if (picked.length >= 4) break;
			if (seenTypes.has(a.chart_type)) continue;
			seenTypes.add(a.chart_type);
			picked.push(a);
		}
		for (const a of sorted) {
			if (picked.length >= 4) break;
			if (!picked.includes(a)) picked.push(a);
		}
		return picked.sort((x, y) => x.lap - y.lap);
	});

	function summary(a) {
		const text = $locale === 'tr' && a.text_tr ? a.text_tr : a.text_en || '';
		// sentence boundary = period NOT after a digit (Turkish ordinals:
		// "15. sıra", "43. tur") and followed by an uppercase start
		const m = text.match(/(?<!\d)[.!?] (?=[A-ZÇĞİÖŞÜ0-9"'])/);
		const cut = m ? m.index : -1;
		let s = cut > 40 && cut < 260 ? text.slice(0, cut + 1) : text;
		if (s.length > 230) s = s.slice(0, 227) + '...';
		return s;
	}

	function show(a) {
		// room-bound moments navigate to their room
		if (a.chart_type === 'energy' && raceId) {
			goto(`/race/${raceId}/energy?driver=${a.driver}`);
			return;
		}
		if ((a.chart_type === 'speed_trace' || a.chart_type === 'track' || a.chart_type === 'traffic') && raceId) {
			if (a.chart_type !== 'traffic') momentFocus.set({ chart: a.chart_type, driver: a.driver, lap: a.lap });
			goto(`/race/${raceId}/telemetry`);
			return;
		}
		selectedDrivers.update((list) => (list.includes(a.driver) ? list : [...list, a.driver]));
		if (a.chart_type === 'pace' || a.chart_type === 'delta') {
			pinnedDriver.set([a.driver]);
		}
		const id = 'section-' + SECTION_BY_TYPE[a.chart_type];
		const el = document.getElementById(id);
		if (!el) return;
		el.scrollIntoView({ behavior: 'smooth', block: 'start' });
		el.classList.remove('pd-flash');
		void el.offsetWidth;
		el.classList.add('pd-flash');
		setTimeout(() => el.classList.remove('pd-flash'), 1700);
		replaceState(location.search + '#' + id, {});
	}
</script>

{#if moments.length > 0}
	<div class="km">
		<span class="km__title">{$t('moments.title')}</span>
		<div class="km__grid">
			{#each moments as m, i (m.chart_type + '-' + m.lap + '-' + m.driver)}
				{@const clip = clipFor(m)}
				<div class="km__card" class:km__card--high={m.severity === 'high'} style="animation-delay: {90 * i}ms">
					<span class="km__k">{$t('moments.lap')} {m.lap} &middot; {m.driver}</span>
					<p class="km__txt">{summary(m)}</p>
					<div class="km__actions">
					<button class="km__go" onclick={() => show(m)}>{$t('moments.show')} &rarr;</button>
					{#if raceId}
						<button class="km__go km__go--watch" onclick={() => goto(`/race/${raceId}/replay?lap=${m.lap}`)}>&#9654; {$t('replay.watch')}</button>
					{/if}
				</div>
				{#if clip}
					<div class="km__radio"><RadioCard {clip} team={teamsMap?.[clip.driver]} lap={clip.lap} compact /></div>
				{/if}
				</div>
			{/each}
		</div>
	</div>
{/if}

<style>
	.km__radio { margin-top: 8px; }
	.km {
		margin-bottom: 1.5rem;
	}
	.km__title {
		display: block;
		font-family: var(--fm, monospace);
		font-size: 10px;
		color: var(--tm, #7d8794);
		letter-spacing: 0.14em;
		text-transform: uppercase;
		margin-bottom: 8px;
	}
	.km__grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
		gap: 2px;
	}
	.km__card {
		background: var(--bg2, #1a1d27);
		border-left: 3px solid #f59e0b;
		padding: 11px 14px;
		display: flex;
		flex-direction: column;
		animation: km-in 0.45s cubic-bezier(0.25, 0.8, 0.35, 1) both;
	}
	.km__card--high {
		border-left-color: var(--ac, #e24b4a);
	}
	@keyframes km-in {
		from { opacity: 0; transform: translateY(7px); }
		to { opacity: 1; transform: translateY(0); }
	}
	.km__k {
		font-family: var(--fm, monospace);
		font-size: 9.5px;
		color: #f07b7a;
		letter-spacing: 0.1em;
		text-transform: uppercase;
	}
	.km__txt {
		font-size: 12.5px;
		line-height: 1.55;
		color: var(--t2, #9ca3af);
		margin: 5px 0 9px;
		flex: 1;
	}
	.km__actions { display: flex; gap: 6px; }
	.km__go {
		align-self: flex-start;
		font-family: var(--fm, monospace);
		font-size: 9.5px;
		font-weight: 700;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: #f07b7a;
		background: none;
		border: 1px solid rgba(226, 75, 74, 0.35);
		padding: 4px 10px;
		cursor: pointer;
		transition: background 0.15s, color 0.15s;
	}
	.km__go:hover {
		background: var(--ac, #e24b4a);
		color: #fff;
	}
	.km__go--watch { color: var(--t2, #9ca3af); border-color: var(--brd, #2e3240); }
	.km__go--radio { color: #22C55E; border-color: rgba(34,197,94,.35); }
	.km__go--radio.playing { background: #22C55E; color: var(--bg-primary); }
	@media (prefers-reduced-motion: reduce) {
		.km__card { animation: none; }
	}
</style>
