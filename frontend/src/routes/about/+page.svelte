<script>
	import { locale } from '$lib/i18n/index.js';

	const L = {
		en: {
			title: 'About',
			subtitle: 'The people behind the data',
			made_by: 'Designed and built by',
			name: 'Bo\u011Fa\u00E7han \u00DClker',
			role: 'Product Owner, Designer & Developer',
			desc: 'RaceRead was born from a simple frustration: F1 broadcasts show what happened, but rarely explain why. The invisible battery strategies, the energy trade-offs at full throttle, the split-second pit wall decisions that decide championships - all hidden behind the spectacle.',
			desc2: 'This platform exists to make that invisible layer visible. Every chart, every annotation, every inference model is designed to answer one question: what really happened in this race?',
			tech_title: 'Built With',
			tech_items: ['SvelteKit + D3.js for interactive visualizations', 'FastAPI (Python) for telemetry processing', 'FastF1 for official F1 timing data', 'Claude API for bilingual race annotations', 'Physics-based energy inference engine'],
			contact_title: 'Contact',
			contact_text: 'For feedback, collaboration, or press inquiries:',
			email: 'boulker24@gmail.com',
			coffee: 'Support the project',
			back: 'Back to Home',
		},
		tr: {
			title: 'Hakk\u0131nda',
			subtitle: 'Verinin arkas\u0131ndaki insanlar',
			made_by: 'Tasarlay\u0131p geli\u015Ftiren',
			name: 'Bo\u011Fa\u00E7han \u00DClker',
			role: '\u00DCr\u00FCn Sahibi, Tasar\u0131mc\u0131 & Geli\u015Ftirici',
			desc: 'RaceRead basit bir hayal k\u0131r\u0131kl\u0131\u011F\u0131ndan do\u011Fdu: F1 yay\u0131nlar\u0131 ne oldu\u011Funu g\u00F6sterir ama neden oldu\u011Funu nadiren a\u00E7\u0131klar. G\u00F6r\u00FCnmez batarya stratejileri, tam gazda enerji \u00F6d\u00FCnle\u015Fimleri, \u015Fampiyonluklar\u0131 belirleyen anl\u0131k pit duvar\u0131 kararlar\u0131 - hepsi g\u00F6sterinin arkas\u0131nda gizli.',
			desc2: 'Bu platform, o g\u00F6r\u00FCnmez katman\u0131 g\u00F6r\u00FCn\u00FCr k\u0131lmak i\u00E7in var. Her grafik, her anotasyon, her \u00E7\u0131kar\u0131m modeli tek bir soruyu yan\u0131tlamak i\u00E7in tasarland\u0131: bu yar\u0131\u015Fta ger\u00E7ekten ne oldu?',
			tech_title: 'Teknolojiler',
			tech_items: ['SvelteKit + D3.js ile interaktif g\u00F6rselle\u015Ftirmeler', 'FastAPI (Python) ile telemetri i\u015Fleme', 'FastF1 ile resmi F1 zamanlama verisi', 'Claude API ile iki dilli yar\u0131\u015F anotasyonlar\u0131', 'Fizik tabanl\u0131 enerji \u00E7\u0131kar\u0131m motoru'],
			contact_title: '\u0130leti\u015Fim',
			contact_text: 'Geri bildirim, i\u015F birli\u011Fi veya bas\u0131n sorular\u0131 i\u00E7in:',
			email: 'boulker24@gmail.com',
			coffee: 'Projeyi destekle',
			back: 'Ana Sayfaya D\u00F6n',
		}
	};

	let tr = $derived(L[$locale] || L.en);
</script>

<svelte:head>
	<title>RaceRead - {tr.title}</title>
	<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" />
</svelte:head>

<div class="ab">
	<nav class="ab__nav">
		<a href="/" class="ab__logo"><img src="/logo@2x.png" alt="RaceRead" class="ab__logo-img" /></a>
		<button class="ab__lang" onclick={() => locale.set($locale === 'en' ? 'tr' : 'en')}>{$locale === 'en' ? 'TR' : 'EN'}</button>
	</nav>

	<div class="ab__content">
		<a href="/" class="ab__back">&larr; {tr.back}</a>

		<div class="ab__hero">
			<h1 class="ab__title">{tr.title}</h1>
			<p class="ab__subtitle">{tr.subtitle}</p>
		</div>

		<!-- Creator -->
		<section class="ab__section">
			<p class="ab__made-by">{tr.made_by}</p>
			<h2 class="ab__name">{tr.name}</h2>
			<p class="ab__role">{tr.role}</p>
		</section>

		<!-- Story -->
		<section class="ab__section">
			<p class="ab__text">{tr.desc}</p>
			<p class="ab__text">{tr.desc2}</p>
		</section>

		<!-- Tech -->
		<section class="ab__section">
			<h3 class="ab__section-title">{tr.tech_title}</h3>
			<ul class="ab__list">
				{#each tr.tech_items as item}<li>{item}</li>{/each}
			</ul>
		</section>

		<!-- Contact -->
		<section class="ab__section ab__section--last">
			<h3 class="ab__section-title">{tr.contact_title}</h3>
			<p class="ab__text">{tr.contact_text}</p>
			<a href="mailto:{tr.email}" class="ab__email">{tr.email}</a>
			<div class="ab__coffee">
				<a href="https://buymeacoffee.com/bogaculker" target="_blank" rel="noopener noreferrer" class="ab__coffee-link">&#9749; {tr.coffee}</a>
			</div>
		</section>

		<footer class="ab__footer">
			<a href="/" class="ab__back">&larr; {tr.back}</a>
		</footer>
	</div>
</div>

<style>
	.ab {
		position: fixed; inset: 0; z-index: 200;
		overflow-y: auto; background: #0F1117; color: #E8E8ED;
		font-family: 'DM Sans', sans-serif; -webkit-font-smoothing: antialiased;
		--fh: 'Space Grotesk', sans-serif;
		--fm: 'JetBrains Mono', monospace;
		--ac: #E24B4A; --bg2: #1A1D27; --brd: #2E3240; --tm: #6B7280;
	}
	.ab__nav {
		position: sticky; top: 0; z-index: 50;
		background: #0F1117; border-bottom: 1px solid rgba(46,50,64,.6);
		padding: 0 2rem; height: 56px;
		display: flex; align-items: center; justify-content: space-between;
	}
	.ab__logo { display: flex; align-items: center; text-decoration: none; }
	.ab__logo:hover { text-decoration: none; }
	.ab__logo-img { height: 40px; width: auto; }
	.ab__lang { font-family: var(--fm); font-size: 10px; font-weight: 700; letter-spacing: .1em; color: var(--ac); background: none; border: 1px solid var(--brd); padding: 5px 12px; cursor: pointer; }

	.ab__content { max-width: 640px; margin: 0 auto; padding: 2rem 2rem 4rem; }
	.ab__back { font-family: var(--fm); font-size: 11px; color: var(--ac); text-decoration: none; text-transform: uppercase; letter-spacing: .08em; }
	.ab__back:hover { text-decoration: none; opacity: .8; }

	.ab__hero { margin: 2.5rem 0 3rem; }
	.ab__title { font-family: var(--fh); font-size: 42px; font-weight: 700; text-transform: uppercase; letter-spacing: -.02em; margin-bottom: .5rem; }
	.ab__subtitle { font-family: var(--fm); font-size: 13px; color: var(--ac); text-transform: uppercase; letter-spacing: .15em; }

	.ab__section { margin-bottom: 2.5rem; padding-bottom: 2rem; border-bottom: 1px solid rgba(46,50,64,.4); }
	.ab__section--last { border-bottom: none; }
	.ab__section-title { font-family: var(--fh); font-size: 18px; font-weight: 700; text-transform: uppercase; border-left: 3px solid var(--ac); padding-left: 1rem; margin-bottom: 1rem; }

	.ab__made-by { font-family: var(--fm); font-size: 11px; color: var(--tm); text-transform: uppercase; letter-spacing: .12em; margin-bottom: .5rem; }
	.ab__name { font-family: var(--fh); font-size: 32px; font-weight: 700; margin-bottom: .25rem; }
	.ab__role { font-family: var(--fm); font-size: 13px; color: var(--ac); letter-spacing: .04em; }

	.ab__text { font-size: 15px; line-height: 1.8; color: #9CA3AF; margin-bottom: .75rem; }

	.ab__list { padding-left: 1.25rem; }
	.ab__list li { font-family: var(--fm); font-size: 12px; color: #9CA3AF; line-height: 1.8; margin-bottom: .3rem; }
	.ab__list li::marker { color: var(--ac); }

	.ab__email { font-family: var(--fm); font-size: 14px; color: var(--ac); text-decoration: none; display: inline-block; margin-top: .5rem; }
	.ab__email:hover { text-decoration: underline; }

	.ab__coffee { margin-top: 1.25rem; }
	.ab__coffee-link { font-family: var(--fm); font-size: 12px; color: #9CA3AF; text-decoration: none; padding: 8px 16px; border: 1px solid var(--brd); transition: all .15s; }
	.ab__coffee-link:hover { color: var(--ac); border-color: var(--ac); text-decoration: none; }

	.ab__footer { margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid rgba(46,50,64,.4); }

	@media (max-width: 640px) {
		.ab__content { padding: 1.5rem 1rem 3rem; }
		.ab__title { font-size: 28px; }
		.ab__name { font-size: 24px; }
		.ab__nav { padding: 0 1rem; }
	}
</style>
