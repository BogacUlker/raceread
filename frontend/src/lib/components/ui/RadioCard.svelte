<!--
	Team radio, F1-broadcast style. Collapsed: a small play button.
	Playing: a lower-third card - team color bar, driver TLA, REC dot,
	live waveform, the transcript "typing in" as the audio plays.
	The Turkish subtitle renders only when the site locale is TR.
	Clips without a transcript (noisy audio) just play, no card text.
-->
<script module>
	// only one radio plays at a time, across every card on the page
	let stopCurrent = null;
</script>

<script>
	import { t, locale } from '$lib/i18n/index.js';
	import { slide } from 'svelte/transition';
	import { TEAM_COLORS } from '$lib/constants.js';

	let { clip, team = '', lap = null, compact = false } = $props();

	let playing = $state(false);
	let ended = $state(false);
	let cur = $state(0);
	let dur = $state(0);
	let audio = null;
	let closeTimer = null;

	function toggle() {
		if (playing) { audio?.pause(); playing = false; stopCurrent = null; return; }
		stopCurrent?.();
		stopCurrent = () => { audio?.pause(); playing = false; };
		clearTimeout(closeTimer);
		if (!audio) {
			audio = new Audio(clip.url);
			audio.onended = () => {
				playing = false; ended = true; cur = dur;
				// linger so the full transcript can be read, then slide shut
				closeTimer = setTimeout(() => { ended = false; }, 3500);
			};
			audio.onerror = () => { playing = false; };
			audio.ontimeupdate = () => { cur = audio.currentTime; dur = audio.duration || 0; };
		}
		if (ended) { audio.currentTime = 0; ended = false; }
		audio.play().catch(() => { playing = false; });
		playing = true;
	}
	$effect(() => () => { audio?.pause(); clearTimeout(closeTimer); });

	let color = $derived(TEAM_COLORS[team] || 'var(--text-muted)');
	let segments = $derived(clip.segments || []);
	let open = $derived((playing || ended) && segments.length > 0);
	function segState(s) {
		if (ended || cur >= s.e) return 'said';
		if (cur >= s.s) return 'saying';
		return 'unsaid';
	}
	function mmss(v) { return Math.floor(v / 60) + ':' + String(Math.floor(v % 60)).padStart(2, '0'); }
</script>

<div class="rc" class:rc--compact={compact}>
	<button class="rc__btn" class:rc__btn--on={playing} onclick={toggle}>
		{playing ? '■' : ended ? '↺' : '▶'}
		<b style="color:{color}">{clip.driver}</b>
		{playing ? mmss(cur) + (dur ? ' / ' + mmss(dur) : '') : $t('replay.radio')}
	</button>

	{#if open}
		<div class="rc__card" transition:slide={{ duration: 260 }}>
			<div class="rc__head">
				<span class="rc__team" style="background:{color}"></span>
				<span class="rc__drv" style="color:{color}">{clip.driver}</span>
				<span class="rc__label">{#if playing}<span class="rc__dot"></span>{/if}TEAM RADIO</span>
				{#if playing}
					<span class="rc__wave"><i></i><i></i><i></i><i></i><i></i><i></i></span>
				{/if}
				<span class="rc__lap">{lap ? ($locale === 'tr' ? 'TUR ' : 'LAP ') + lap : ''}</span>
			</div>
			<div class="rc__quote" lang="en">
				{#each segments as s, i}<span class="rc__seg rc__seg--{segState(s)}">{i > 0 ? ' ' : ''}{s.t}</span>{/each}
			</div>
			{#if $locale === 'tr' && segments.some((s) => s.tr)}
				<div class="rc__tr">{segments.map((s) => s.tr || '').join(' ')}</div>
			{/if}
			<div class="rc__tag">{$t('replay.auto_transcript')}</div>
		</div>
	{/if}
</div>

<style>
	.rc__btn {
		display: inline-flex; gap: 6px; align-items: baseline;
		background: none; border: 1px solid var(--brd, var(--border)); color: var(--text-secondary);
		font-family: var(--fm, var(--font-mono)), monospace; font-size: 10px; padding: 3px 8px; cursor: pointer;
	}
	.rc__btn:hover { border-color: #6C98FF; color: var(--text-primary); }
	.rc__btn--on { border-color: #6C98FF; color: var(--text-primary); }
	.rc__btn b { font-weight: 700; }

	.rc__card { margin-top: 6px; max-width: 440px; background: rgba(8, 9, 13, .92); border: 1px solid var(--brd, var(--border)); }
	.rc--compact .rc__card { max-width: 100%; }
	.rc__head { display: flex; align-items: stretch; border-bottom: 1px solid var(--brd, var(--border)); }
	.rc__team { width: 5px; flex: 0 0 5px; }
	.rc__drv { font-family: var(--fm, var(--font-mono)), monospace; font-weight: 700; font-size: 13px; letter-spacing: .04em; padding: 7px 10px; }
	.rc__label { display: flex; align-items: center; gap: 6px; font-family: var(--fm, var(--font-mono)), monospace; font-size: 9px; letter-spacing: .16em; color: var(--text-secondary); }
	.rc__dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); animation: rc-pulse 1.1s infinite; }
	@keyframes rc-pulse { 50% { opacity: .25; } }
	.rc__wave { display: flex; align-items: center; gap: 2px; margin-left: auto; padding-right: 10px; }
	.rc__wave i { width: 3px; background: #6C98FF; animation: rc-eq .9s infinite ease-in-out; }
	.rc__wave i:nth-child(1) { height: 6px; } .rc__wave i:nth-child(2) { height: 12px; animation-delay: .15s; }
	.rc__wave i:nth-child(3) { height: 15px; animation-delay: .3s; } .rc__wave i:nth-child(4) { height: 9px; animation-delay: .45s; }
	.rc__wave i:nth-child(5) { height: 13px; animation-delay: .6s; } .rc__wave i:nth-child(6) { height: 5px; animation-delay: .75s; }
	@keyframes rc-eq { 50% { transform: scaleY(.35); } }
	.rc__lap { font-family: var(--fm, var(--font-mono)), monospace; font-size: 9px; color: var(--text-muted); align-self: center; padding-right: 10px; margin-left: auto; }
	.rc__wave + .rc__lap { margin-left: 0; }
	.rc__quote { font-family: var(--fm, var(--font-mono)), monospace; font-weight: 700; font-size: 12.5px; line-height: 1.65; text-transform: uppercase; letter-spacing: .02em; padding: 10px 12px 4px; }
	.rc__seg--unsaid { color: #565D6B; }
	.rc__seg--said { color: var(--text-primary); }
	.rc__seg--saying { color: var(--text-primary); border-bottom: 2px solid #6C98FF; }
	.rc__tr { font-size: 11.5px; color: var(--text-muted); padding: 5px 12px 0; font-style: italic; line-height: 1.55; }
	.rc__tag { font-family: var(--fm, var(--font-mono)), monospace; font-size: 8.5px; letter-spacing: .14em; color: #565D6B; padding: 8px 12px 9px; text-transform: uppercase; }
	@media (prefers-reduced-motion: reduce) { .rc__dot, .rc__wave i { animation: none; } }
</style>
