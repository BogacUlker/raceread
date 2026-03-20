<script>
	import { locale } from '$lib/i18n/index.js';

	const L = {
		en: {
			title: 'How It Works',
			subtitle: 'From raw telemetry to race intelligence',
			s1_title: 'What is RaceRead?',
			s1_text: 'RaceRead is a post-race telemetry analysis platform for Formula 1. After each Grand Prix, we process high-frequency sensor data and transform it into interactive charts, AI-generated annotations, and energy inference models. Our goal is to reveal the invisible strategies that decide modern F1 races.',
			s2_title: 'Data Source',
			s2_text: 'All telemetry data comes from FastF1, an open-source Python library that accesses official F1 timing data. For each race we collect:',
			s2_items: ['Speed, throttle, brake, gear and RPM at ~4Hz sampling rate', 'Lap times with sector splits (S1, S2, S3)', 'Tyre compound, tyre age, and pit stop timing', 'Track position (X, Y coordinates) for circuit mapping', 'Weather conditions: air temp, track temp, humidity, rainfall', 'Race control messages: Safety Car, VSC, flags'],
			s3_title: 'Energy Inference',
			s3_text: 'In 2026, the MGU-K produces 350kW and the battery holds 4MJ of energy. These figures are not directly measured in public telemetry. RaceRead infers energy states using a physics-based model:',
			s3_steps: ['Calculate acceleration from speed telemetry (Gaussian smoothed)', 'Build an ICE-only baseline: expected acceleration at each speed when only the engine is working', 'Compare observed acceleration against the baseline to classify each telemetry sample'],
			s3_states: [
				{ name: 'DEPLOYING', color: '#22C55E', desc: 'Battery adding power to ICE. Car is faster than engine alone.' },
				{ name: 'HARVESTING', color: '#3B82F6', desc: 'Regenerative braking or lift-and-coast. Battery is charging.' },
				{ name: 'CLIPPING', color: '#F59E0B', desc: 'At full throttle, ICE power is stolen to charge battery. Car is slower despite driver pushing.' },
				{ name: 'NEUTRAL', color: '#6B7280', desc: 'No significant energy transfer detected.' },
			],
			s3_badge: 'All energy data is inferred, never measured. Every energy chart displays an "inferred" badge.',
			s4_title: 'AI Annotations',
			s4_text: 'RaceRead uses Claude API to generate bilingual (TR/EN) race annotations. These are not live chat responses. They are pre-computed once per race based on detected events:',
			s4_items: ['Pace anomaly: lap time deviates >0.5s from rolling average', 'Energy shift: deploy or clip percentage changes >2x between laps', 'Safety Car / VSC deployment', 'Pit stops and strategy calls', 'Position changes >2 places', 'Fastest lap achievements'],
			s5_title: 'Charts & Visualizations',
			s5_text: 'Every chart is interactive. Hover for details, click to pin drivers, filter by team or driver. Available analysis:',
			s5_charts: ['Race Pace: lap-by-lap comparison with gap-to-leader mode', 'Strategy Timeline: tyre stints with SC/VSC overlays', 'Energy Profile: normalized deploy/harvest/clip distribution', 'Delta Matrix: driver-to-driver median pace comparison', 'Speed Trace: two-driver speed overlay by track distance', 'Track Map: telemetry plotted on circuit layout', 'Traffic Analysis: dirty air impact per driver', 'Qualifying Animation: head-to-head lap replay on track'],
			s6_title: 'Open & Transparent',
			s6_text: 'RaceRead is built by a small team passionate about F1 data. All energy states are clearly labeled as inferred. We use FastF1 as our sole data source. No paywalls, no ads.',
			back: 'Back to Home',
		},
		tr: {
			title: 'Nas\u0131l \u00C7al\u0131\u015F\u0131r',
			subtitle: 'Ham telemetriden yar\u0131\u015F istihbarat\u0131na',
			s1_title: 'RaceRead Nedir?',
			s1_text: 'RaceRead, Formula 1 i\u00E7in yar\u0131\u015F sonras\u0131 telemetri analiz platformudur. Her Grand Prix sonras\u0131nda y\u00FCksek frekansl\u0131 sens\u00F6r verisini i\u015Fler, interaktif grafiklere, AI destekli anotasyonlara ve enerji \u00E7\u0131kar\u0131m modellerine d\u00F6n\u00FC\u015Ft\u00FCr\u00FCr\u00FCz. Amac\u0131m\u0131z modern F1 yar\u0131\u015Flar\u0131n\u0131 belirleyen g\u00F6r\u00FCnmez stratejileri ortaya koymakt\u0131r.',
			s2_title: 'Veri Kayna\u011F\u0131',
			s2_text: 'T\u00FCm telemetri verisi, resmi F1 zamanlama verisine eri\u015Fen a\u00E7\u0131k kaynak Python k\u00FCt\u00FCphanesi FastF1\'den gelir. Her yar\u0131\u015F i\u00E7in toplad\u0131\u011F\u0131m\u0131z veriler:',
			s2_items: ['H\u0131z, gaz, fren, vites ve devir bilgisi (~4Hz \u00F6rnekleme)', 'Sekt\u00F6r ayr\u0131nt\u0131l\u0131 tur s\u00FCreleri (S1, S2, S3)', 'Lastik bile\u015Feni, lastik ya\u015F\u0131 ve pit stop zamanlamalar\u0131', 'Pist konumu (X, Y koordinatlar\u0131) ile devre haritalama', 'Hava ko\u015Fullar\u0131: hava s\u0131cakl\u0131\u011F\u0131, pist s\u0131cakl\u0131\u011F\u0131, nem, ya\u011F\u0131\u015F', 'Yar\u0131\u015F kontrol mesajlar\u0131: G\u00FCvenlik Arac\u0131, VSC, bayraklar'],
			s3_title: 'Enerji \u00C7\u0131kar\u0131m\u0131',
			s3_text: '2026\'da MGU-K 350kW \u00FCretir ve batarya 4MJ enerji ta\u015F\u0131r. Bu rakamlar halka a\u00E7\u0131k telemetride do\u011Frudan \u00F6l\u00E7\u00FClmez. RaceRead, fizik tabanl\u0131 bir model kullanarak enerji durumlar\u0131n\u0131 \u00E7\u0131kar\u0131r:',
			s3_steps: ['H\u0131z telemetrisinden ivme hesaplama (Gauss d\u00FCzle\u015Ftirmeli)', 'Yaln\u0131zca motor \u00E7al\u0131\u015F\u0131rken beklenen ivmeyi g\u00F6steren ICE taban \u00E7izgisi olu\u015Fturma', 'G\u00F6zlenen ivmeyi taban \u00E7izgisiyle kar\u015F\u0131la\u015Ft\u0131rarak her telemetri \u00F6rne\u011Fini s\u0131n\u0131fland\u0131rma'],
			s3_states: [
				{ name: 'DEPLOYING', color: '#22C55E', desc: 'Batarya motora g\u00FC\u00E7 ekliyor. Ara\u00E7 yaln\u0131zca motordan daha h\u0131zl\u0131.' },
				{ name: 'HARVESTING', color: '#3B82F6', desc: 'Rejeneratif frenleme veya gaz kald\u0131rma. Batarya \u015Farj oluyor.' },
				{ name: 'CLIPPING', color: '#F59E0B', desc: 'Tam gazda ICE g\u00FCc\u00FC bataryay\u0131 \u015Farj etmek i\u00E7in \u00E7al\u0131n\u0131yor. Pilot bast\u0131\u011F\u0131 halde ara\u00E7 yava\u015F.' },
				{ name: 'NEUTRAL', color: '#6B7280', desc: '\u00D6nemli bir enerji transferi tespit edilmedi.' },
			],
			s3_badge: 'T\u00FCm enerji verileri \u00E7\u0131kar\u0131msald\u0131r, asla do\u011Frudan \u00F6l\u00E7\u00FCm de\u011Fildir. Her enerji grafi\u011Finde "\u00E7\u0131kar\u0131msal" etiketi g\u00F6r\u00FCnt\u00FClenir.',
			s4_title: 'AI Anotasyonlar',
			s4_text: 'RaceRead, iki dilli (TR/EN) yar\u0131\u015F anotasyonlar\u0131 \u00FCretmek i\u00E7in Claude API kullan\u0131r. Bunlar canl\u0131 sohbet yan\u0131tlar\u0131 de\u011Fildir. Tespit edilen olaylara dayal\u0131 olarak yar\u0131\u015F ba\u015F\u0131na bir kez \u00F6nceden hesaplan\u0131r:',
			s4_items: ['Tempo anomalisi: tur s\u00FCresi hareketli ortalamadan >0.5s sapma', 'Enerji de\u011Fi\u015Fimi: deploy veya clip y\u00FCzdesi turlar aras\u0131nda >2x de\u011Fi\u015Fim', 'G\u00FCvenlik Arac\u0131 / VSC', 'Pit stoplar ve strateji kararlar\u0131', '>2 s\u0131ra pozisyon de\u011Fi\u015Fiklikleri', 'En h\u0131zl\u0131 tur ba\u015Far\u0131lar\u0131'],
			s5_title: 'Grafikler ve G\u00F6rselle\u015Ftirmeler',
			s5_text: 'Her grafik interaktiftir. Detay i\u00E7in \u00FCzerine gelin, pilotlar\u0131 sabitlemek i\u00E7in t\u0131klay\u0131n, tak\u0131m veya pilota g\u00F6re filtreleyin. Mevcut analizler:',
			s5_charts: ['Yar\u0131\u015F Temposu: lidere fark moduyla tur tur kar\u015F\u0131la\u015Ft\u0131rma', 'Strateji Zaman \u00C7izelgesi: SC/VSC katmanlar\u0131yla lastik stintleri', 'Enerji Profili: normalize deploy/harvest/clip da\u011F\u0131l\u0131m\u0131', 'Delta Matrisi: pilot-pilot medyan tempo kar\u015F\u0131la\u015Ft\u0131rmas\u0131', 'H\u0131z Grafi\u011Fi: pist mesafesine g\u00F6re iki pilotlu h\u0131z kar\u015F\u0131la\u015Ft\u0131rmas\u0131', 'Pist Haritas\u0131: devre d\u00FCzeninde telemetri g\u00F6rsellemesi', 'Trafik Analizi: pilot ba\u015F\u0131na kirli hava etkisi', 'S\u0131ralama Animasyonu: pistte kafa kafaya tur tekrar\u0131'],
			s6_title: 'A\u00E7\u0131k ve \u015Eeffaf',
			s6_text: 'RaceRead, F1 verisine tutkulu k\u00FC\u00E7\u00FCk bir ekip taraf\u0131ndan olu\u015Fturulmu\u015Ftur. T\u00FCm enerji durumlar\u0131 a\u00E7\u0131k\u00E7a \u00E7\u0131kar\u0131msal olarak etiketlenir. Tek veri kayna\u011F\u0131m\u0131z FastF1\'dir. Reklam yok, \u00F6deme duvar\u0131 yok.',
			back: 'Ana Sayfaya D\u00F6n',
		}
	};

	let tr = $derived(L[$locale] || L.en);
</script>

<svelte:head>
	<title>RaceRead - {tr.title}</title>
	<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" />
</svelte:head>

<div class="hw">
	<nav class="hw__nav">
		<a href="/" class="hw__logo"><img src="/logo@2x.png" alt="RaceRead" class="hw__logo-img" /></a>
		<button class="hw__lang" onclick={() => locale.set($locale === 'en' ? 'tr' : 'en')}>{$locale === 'en' ? 'TR' : 'EN'}</button>
	</nav>

	<div class="hw__content">
		<a href="/" class="hw__back">&larr; {tr.back}</a>

		<div class="hw__hero">
			<h1 class="hw__title">{tr.title}</h1>
			<p class="hw__subtitle">{tr.subtitle}</p>
		</div>

		<!-- 1. What is RaceRead -->
		<section class="hw__section">
			<h2 class="hw__section-title">{tr.s1_title}</h2>
			<p class="hw__text">{tr.s1_text}</p>
		</section>

		<!-- 2. Data Source -->
		<section class="hw__section">
			<h2 class="hw__section-title">{tr.s2_title}</h2>
			<p class="hw__text">{tr.s2_text}</p>
			<ul class="hw__list">
				{#each tr.s2_items as item}<li>{item}</li>{/each}
			</ul>
		</section>

		<!-- 3. Energy Inference -->
		<section class="hw__section">
			<h2 class="hw__section-title">{tr.s3_title}</h2>
			<p class="hw__text">{tr.s3_text}</p>
			<ol class="hw__list hw__list--numbered">
				{#each tr.s3_steps as step}<li>{step}</li>{/each}
			</ol>
			<div class="hw__states">
				{#each tr.s3_states as state}
					<div class="hw__state" style="border-left-color: {state.color}">
						<span class="hw__state-name" style="color: {state.color}">{state.name}</span>
						<span class="hw__state-desc">{state.desc}</span>
					</div>
				{/each}
			</div>
			<p class="hw__badge-note">{tr.s3_badge}</p>
		</section>

		<!-- 4. AI Annotations -->
		<section class="hw__section">
			<h2 class="hw__section-title">{tr.s4_title}</h2>
			<p class="hw__text">{tr.s4_text}</p>
			<ul class="hw__list">
				{#each tr.s4_items as item}<li>{item}</li>{/each}
			</ul>
		</section>

		<!-- 5. Charts -->
		<section class="hw__section">
			<h2 class="hw__section-title">{tr.s5_title}</h2>
			<p class="hw__text">{tr.s5_text}</p>
			<div class="hw__chart-grid">
				{#each tr.s5_charts as chart}
					<div class="hw__chart-item">{chart}</div>
				{/each}
			</div>
		</section>

		<!-- 6. Open -->
		<section class="hw__section">
			<h2 class="hw__section-title">{tr.s6_title}</h2>
			<p class="hw__text">{tr.s6_text}</p>
		</section>

		<footer class="hw__footer">
			<a href="/" class="hw__back">&larr; {tr.back}</a>
		</footer>
	</div>
</div>

<style>
	.hw {
		position: fixed; inset: 0; z-index: 200;
		overflow-y: auto; background: #0F1117; color: #E8E8ED;
		font-family: 'DM Sans', sans-serif; -webkit-font-smoothing: antialiased;
		--fh: 'Space Grotesk', sans-serif;
		--fm: 'JetBrains Mono', monospace;
		--ac: #E24B4A; --bg2: #1A1D27; --brd: #2E3240; --tm: #6B7280;
	}

	.hw__nav {
		position: sticky; top: 0; z-index: 50;
		background: #0F1117; border-bottom: 1px solid rgba(46,50,64,.6);
		padding: 0 2rem; height: 56px;
		display: flex; align-items: center; justify-content: space-between;
	}
	.hw__logo { display: flex; align-items: center; text-decoration: none; }
	.hw__logo:hover { text-decoration: none; }
	.hw__logo-img { height: 40px; width: auto; }
	.hw__lang { font-family: var(--fm); font-size: 10px; font-weight: 700; letter-spacing: .1em; color: var(--ac); background: none; border: 1px solid var(--brd); padding: 5px 12px; cursor: pointer; }

	.hw__content { max-width: 780px; margin: 0 auto; padding: 2rem 2rem 4rem; }

	.hw__back { font-family: var(--fm); font-size: 11px; color: var(--ac); text-decoration: none; text-transform: uppercase; letter-spacing: .08em; }
	.hw__back:hover { text-decoration: none; opacity: .8; }

	.hw__hero { margin: 2.5rem 0 3rem; }
	.hw__title { font-family: var(--fh); font-size: 42px; font-weight: 700; text-transform: uppercase; letter-spacing: -.02em; line-height: 1.1; margin-bottom: .5rem; }
	.hw__subtitle { font-family: var(--fm); font-size: 13px; color: var(--ac); text-transform: uppercase; letter-spacing: .15em; }

	.hw__section { margin-bottom: 3rem; padding-bottom: 2.5rem; border-bottom: 1px solid rgba(46,50,64,.4); }
	.hw__section:last-of-type { border-bottom: none; }
	.hw__section-title { font-family: var(--fh); font-size: 22px; font-weight: 700; text-transform: uppercase; letter-spacing: -.01em; margin-bottom: 1rem; border-left: 3px solid var(--ac); padding-left: 1rem; }
	.hw__text { font-size: 15px; line-height: 1.8; color: #9CA3AF; margin-bottom: 1rem; }

	.hw__list { padding-left: 1.25rem; margin-bottom: 1rem; }
	.hw__list li { font-family: var(--fm); font-size: 12px; color: #9CA3AF; line-height: 1.8; margin-bottom: .3rem; }
	.hw__list li::marker { color: var(--ac); }
	.hw__list--numbered li::marker { color: var(--ac); font-weight: 700; }

	.hw__states { display: grid; grid-template-columns: repeat(2, 1fr); gap: 2px; margin: 1.5rem 0; }
	.hw__state { background: var(--bg2); padding: 1.1rem 1.25rem; border-left: 3px solid; }
	.hw__state-name { font-family: var(--fm); font-size: 12px; font-weight: 700; display: block; margin-bottom: 4px; text-transform: uppercase; letter-spacing: .06em; }
	.hw__state-desc { font-size: 13px; color: #9CA3AF; line-height: 1.5; }

	.hw__badge-note { font-family: var(--fm); font-size: 11px; color: var(--ac); background: rgba(226,75,74,.06); padding: .75rem 1rem; border-left: 3px solid var(--ac); margin-top: 1rem; }

	.hw__chart-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 2px; margin-top: 1rem; }
	.hw__chart-item { font-family: var(--fm); font-size: 12px; color: #9CA3AF; background: var(--bg2); padding: .9rem 1.1rem; border-left: 2px solid var(--brd); transition: border-color .2s; }
	.hw__chart-item:hover { border-left-color: var(--ac); }

	.hw__footer { margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid rgba(46,50,64,.4); }

	@media (max-width: 640px) {
		.hw__content { padding: 1.5rem 1rem 3rem; }
		.hw__title { font-size: 28px; }
		.hw__states { grid-template-columns: 1fr; }
		.hw__chart-grid { grid-template-columns: 1fr; }
		.hw__nav { padding: 0 1rem; }
	}
</style>
