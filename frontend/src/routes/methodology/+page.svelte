<!--
	Methodology - how the energy inference works and how much to trust it.
	Long-form copy is inline per locale (story-page pattern) rather than
	i18n keys; the live confidence table reads validation_confidence from
	the races/classics APIs.
-->
<script>
	import { t, locale } from '$lib/i18n/index.js';

	let { data } = $props();
	let tr = $derived($locale === 'tr');

	let rows = $derived(
		[...(data.races || []).map((r) => ({ ...r, era: '2026' })), ...(data.classics || []).map((r) => ({ ...r, era: '2021' }))]
			.filter((r) => r.validation_confidence != null)
			.sort((a, b) => b.validation_confidence - a.validation_confidence)
	);

	function scoreColor(v) {
		if (v >= 80) return '#22C55E';
		if (v >= 70) return '#F59E0B';
		return '#E24B4A';
	}
</script>

<svelte:head>
	<title>{tr ? 'Metodoloji' : 'Methodology'} - RaceRead</title>
</svelte:head>

<div class="mt">
	<div class="mt__inner">
		<p class="mt__eyebrow">{tr ? 'METODOLOJİ' : 'METHODOLOGY'}</p>
		<h1 class="mt__title">{tr ? 'Enerji verisi nereden geliyor?' : 'Where does the energy data come from?'}</h1>
		<p class="mt__lead">
			{tr
				? 'F1, batarya ve ERS verilerini yayınlamaz. RaceRead’deki her enerji durumu, halka açık telemetriden fizik yoluyla çıkarılır - bu sayfa yöntemin nasıl çalıştığını ve sonuçlara ne kadar güvenmen gerektiğini anlatır.'
				: 'F1 does not broadcast battery or ERS data. Every energy state on RaceRead is inferred from public telemetry through physics - this page explains how the method works and how much to trust the results.'}
		</p>

		<h2 class="mt__h2">{tr ? 'Yöntem: ivme kalıntı analizi' : 'The method: acceleration residual analysis'}</h2>
		<p>
			{tr
				? 'Elektrik motoru itiş sağladığında araç, içten yanmalı motorun tek başına üretebileceğinden daha sert hızlanır. Bu fark ölçülebilir - ve tek gereken veri, zaten yayınlanan hız kanalıdır.'
				: 'When the electric motor deploys, the car accelerates harder than the combustion engine alone could manage. That difference is measurable - and the only input needed is the speed channel that is already public.'}
		</p>
		<ol class="mt__steps">
			<li><b>{tr ? 'İvme' : 'Acceleration'}</b> - {tr ? 'gerçek hız verisinden sonlu farklarla hesaplanır, sensör gürültüsü Gaussian filtreyle yumuşatılır.' : 'computed from real speed data via finite differences, smoothed with a Gaussian filter to tame sensor noise.'}</li>
			<li><b>{tr ? 'ICE taban çizgisi' : 'ICE baseline'}</b> - {tr ? 'aynı aracın o yarıştaki tam gaz örneklerinden, hız aralığı başına medyan ivme + standart sapma zarfı kurulur. Model her araç ve her yarış için kendini yeniden kalibre eder.' : 'per speed bin, the median acceleration + a standard-deviation envelope is built from that same car’s full-throttle samples in that race. The model recalibrates itself for every car and every race.'}</li>
			<li><b>{tr ? 'Sınıflama' : 'Classification'}</b> - {tr ? 'her örnek zarfa göre etiketlenir: belirgin üstünde' : 'each sample is labelled against the envelope: significantly above'} &rarr; <span class="mt__tag" style="background:#22C55E">DEPLOY</span>, {tr ? 'tam gazda belirgin altında' : 'significantly below at full throttle'} &rarr; <span class="mt__tag" style="background:#F59E0B">CLIP</span>, {tr ? 'fren eşiğini aşan yavaşlama' : 'deceleration beyond the braking threshold'} &rarr; <span class="mt__tag" style="background:#3B82F6">HARVEST</span>, {tr ? 'gerisi' : 'the rest'} &rarr; <span class="mt__tag" style="background:#6B7280">NEUTRAL</span>.</li>
			<li><b>{tr ? 'Doğrulama' : 'Validation'}</b> - {tr ? 'sonuçlar o dönemin fiziğine karşı test edilir: güç bütçeleri, tur başına hasat limitleri, deploy süreleri. Bu testlerin sonucu aşağıdaki güven skorudur.' : 'results are tested against era physics: power budgets, per-lap harvest limits, deploy durations. The outcome of those tests is the confidence score below.'}</li>
		</ol>

		<div class="mt__diagram">
			<svg viewBox="0 0 560 200" role="img" aria-label={tr ? 'İvme zarfı şeması' : 'Acceleration envelope diagram'}>
				<text x="12" y="18" fill="#7D8794" font-size="10" font-family="monospace">{tr ? 'İVME' : 'ACCEL'}</text>
				<text x="500" y="192" fill="#7D8794" font-size="10" font-family="monospace">{tr ? 'HIZ' : 'SPEED'}</text>
				<path d="M40,60 C160,75 320,105 520,135" fill="none" stroke="#E8E8ED" stroke-width="1.6" stroke-dasharray="5,4" />
				<path d="M40,40 C160,55 320,85 520,115 L520,155 C320,125 160,95 40,80 Z" fill="rgba(232,232,237,.06)" />
				<text x="250" y="86" fill="#9CA3AF" font-size="10" font-family="monospace">{tr ? 'ICE zarfı (o aracın kendi verisi)' : 'ICE envelope (that car’s own data)'}</text>
				<circle cx="140" cy="38" r="4" fill="#22C55E" /><text x="150" y="34" fill="#22C55E" font-size="10" font-family="monospace">DEPLOY</text>
				<circle cx="330" cy="128" r="4" fill="#F59E0B" /><text x="340" y="124" fill="#F59E0B" font-size="10" font-family="monospace">CLIP</text>
				<circle cx="440" cy="180" r="4" fill="#3B82F6" /><text x="450" y="176" fill="#3B82F6" font-size="10" font-family="monospace">HARVEST</text>
				<circle cx="260" cy="100" r="4" fill="#6B7280" />
			</svg>
		</div>

		<h2 class="mt__h2">{tr ? '2021 klasikleri neden daha düşük skorlu?' : 'Why do the 2021 classics score lower?'}</h2>
		<p>
			{tr
				? 'Yöntem aynı, sinyal farklı. 2021 hibritlerinin MGU-K’sı 120 kW üretiyordu; 2026 kurallarında elektrik güç ~350 kW. Elektrik katkısı ivme içinde ne kadar küçükse, gürültüden ayırmak o kadar zorlaşır.'
				: 'Same method, different signal. The 2021 hybrid’s MGU-K produced 120 kW; under the 2026 rules electric power is ~350 kW. The smaller the electric contribution inside the acceleration trace, the harder it is to separate from noise.'}
		</p>
		<div class="mt__eras">
			<div class="mt__era">
				<span class="mt__era-y">2026</span>
				<ul>
					<li>{tr ? 'Elektrik güç' : 'Electric power'}: <b>~350 kW</b></li>
					<li>{tr ? 'Taktiksel deploy - net desenler' : 'Tactical deployment - clear patterns'}</li>
					<li>{tr ? 'Güven' : 'Confidence'}: <b style="color:#22C55E">80-90</b></li>
				</ul>
			</div>
			<div class="mt__era">
				<span class="mt__era-y">2021</span>
				<ul>
					<li>{tr ? 'Elektrik güç' : 'Electric power'}: <b>120 kW</b></li>
					<li>{tr ? 'Sürekli deploy - küçük kalıntılar' : 'Continuous deployment - small residuals'}</li>
					<li>{tr ? 'Güven' : 'Confidence'}: <b style="color:#F59E0B">57-87</b></li>
				</ul>
			</div>
		</div>
		<p>
			{tr
				? 'Pratik öneri: 2021’de deploy/clip oranlarını pilotlar arası karşılaştırma için kullan - aynı model, aynı gürültü, sıralama anlamlı. Tekil yüzdeleri ise kesin ölçüm gibi değil, yön göstergesi gibi oku.'
				: 'Practical guidance: in 2021, use deploy/clip ratios to compare drivers - same model, same noise, the ranking is meaningful. Read individual percentages as directional, not as precise measurements.'}
		</p>

		<h2 class="mt__h2">{tr ? 'Yarış başına güven skoru' : 'Confidence score per race'}</h2>
		<div class="mt__table">
			<div class="mt__row mt__row--head">
				<span>{tr ? 'Yarış' : 'Race'}</span><span>{tr ? 'Dönem' : 'Era'}</span><span>{tr ? 'Skor' : 'Score'}</span><span></span>
			</div>
			{#each rows as r}
				<a href="/race/{r.id}" class="mt__row">
					<span>{r.name?.replace(' Grand Prix', ' GP')}</span>
					<span class="mt__era-tag">{r.era}</span>
					<span style="color:{scoreColor(r.validation_confidence)}">{r.validation_confidence.toFixed(1)}</span>
					<span class="mt__bar"><i style="width:{r.validation_confidence}%; background:{scoreColor(r.validation_confidence)}"></i></span>
				</a>
			{/each}
		</div>

		<h2 class="mt__h2">{tr ? 'Sınırlar - açıkça' : 'Limitations - plainly'}</h2>
		<ul class="mt__limits">
			<li>{tr ? 'Bu bir çıkarımdır, ölçüm değil. FIA’nın gördüğü gerçek batarya verisiyle hiçbir bağı yok.' : 'This is inference, not measurement. It has no connection to the real battery data the FIA sees.'}</li>
			<li>{tr ? 'Rüzgar, slipstream ve yakıt etkisi ivmeye karışır; kısa süreli durumlarda yanlış etiket mümkündür.' : 'Wind, slipstream and fuel effects contaminate acceleration; short-lived states can be mislabelled.'}</li>
			<li>{tr ? 'Skoru 70’in altındaki yarışlarda (ör. Monza ve Bahreyn 2021) enerji grafiklerini yalnızca desen düzeyinde oku.' : 'For races scoring under 70 (e.g. Monza and Bahrain 2021), read the energy charts at pattern level only.'}</li>
			<li>{tr ? 'Islak yarışlarda tam gaz örneği azaldığı için taban çizgisi zayıflar.' : 'Wet races weaken the baseline because full-throttle samples are scarce.'}</li>
		</ul>

		<p class="mt__foot">
			{tr
				? 'Kaynak veri: FastF1 üzerinden halka açık zamanlama ve telemetri akışları. Çıkarım kodu bu sitenin backend’inde çalışır; her yarışın doğrulama raporu veriyle birlikte saklanır.'
				: 'Source data: public timing and telemetry streams via FastF1. The inference code runs in this site’s backend; every race’s validation report is stored alongside its data.'}
		</p>
	</div>
</div>

<style>
	.mt { min-height: 100vh; background: var(--bg-primary, #0F1117); color: var(--text-primary, #E8E8ED); padding: 3rem 1.5rem 5rem; }
	.mt__inner { max-width: 760px; margin: 0 auto; }
	.mt__eyebrow { font-family: var(--font-mono); font-size: 10px; letter-spacing: .16em; color: var(--accent, #E24B4A); margin: 0 0 6px; }
	.mt__title { font-family: var(--font-heading); font-size: clamp(26px, 4vw, 34px); font-weight: 700; letter-spacing: -.02em; margin: 0 0 12px; }
	.mt__lead { font-size: 15.5px; line-height: 1.7; color: var(--text-secondary, #9CA3AF); max-width: 62ch; }
	.mt__h2 { font-family: var(--font-heading); font-size: 18px; font-weight: 700; margin: 40px 0 10px; letter-spacing: -.01em; }
	.mt p { font-size: 14px; line-height: 1.7; color: var(--text-secondary, #9CA3AF); max-width: 68ch; }
	.mt__steps { padding-left: 20px; color: var(--text-secondary, #9CA3AF); font-size: 14px; line-height: 1.7; max-width: 68ch; }
	.mt__steps li { margin-bottom: 10px; }
	.mt__steps b { color: var(--text-primary, #E8E8ED); }
	.mt__tag { font-family: var(--font-mono); font-size: 9px; font-weight: 700; color: #000; padding: 1px 6px; vertical-align: middle; }
	.mt__diagram { background: var(--bg-secondary, #1A1D27); border: 1px solid var(--border, #2E3240); padding: 14px; margin: 18px 0; }
	.mt__diagram svg { width: 100%; height: auto; display: block; }
	.mt__eras { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 16px 0; }
	@media (max-width: 560px) { .mt__eras { grid-template-columns: 1fr; } }
	.mt__era { background: var(--bg-secondary, #1A1D27); border: 1px solid var(--border, #2E3240); padding: 14px 16px; }
	.mt__era-y { font-family: var(--font-heading); font-size: 20px; font-weight: 700; }
	.mt__era ul { list-style: none; padding: 0; margin: 8px 0 0; font-size: 13px; color: var(--text-secondary, #9CA3AF); }
	.mt__era li { margin-bottom: 5px; }
	.mt__era b { color: var(--text-primary, #E8E8ED); }
	.mt__table { border: 1px solid var(--border, #2E3240); margin: 14px 0; }
	.mt__row { display: grid; grid-template-columns: 1fr 52px 52px 130px; gap: 12px; align-items: center; padding: 7px 14px; font-family: var(--font-mono); font-size: 11.5px; color: var(--text-secondary, #9CA3AF); text-decoration: none; border-bottom: 1px solid rgba(46,50,64,.5); }
	a.mt__row:hover { background: var(--bg-secondary, #1A1D27); color: var(--text-primary, #E8E8ED); text-decoration: none; }
	.mt__row--head { font-size: 9px; text-transform: uppercase; letter-spacing: .08em; color: var(--text-muted, #7D8794); border-bottom: 1px solid var(--border, #2E3240); }
	.mt__era-tag { color: var(--text-muted, #7D8794); }
	.mt__bar { height: 5px; background: rgba(46,50,64,.6); display: block; }
	.mt__bar i { display: block; height: 100%; }
	.mt__limits { padding-left: 20px; color: var(--text-secondary, #9CA3AF); font-size: 14px; line-height: 1.7; max-width: 68ch; }
	.mt__limits li { margin-bottom: 8px; }
	.mt__foot { font-size: 12.5px; color: var(--text-muted, #7D8794); border-top: 1px solid var(--border, #2E3240); padding-top: 16px; margin-top: 36px; }
	@media (max-width: 640px) { .mt__row { grid-template-columns: 1fr 44px 44px; } .mt__bar { display: none; } }
</style>
