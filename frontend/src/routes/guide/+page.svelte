<!--
	How-to guide - what each page shows and how to read the data.
	Long-form copy inline per locale (methodology-page pattern).
-->
<script>
	import { locale } from '$lib/i18n/index.js';
	let tr = $derived($locale === 'tr');

	const S = [
		{
			id: 'dashboard',
			tr: { title: 'Yarış sayfasını okumak', items: [
				['Yarış Hikayesi & Kilit Anlar', 'Sayfanın tepesindeki hikaye yarışın özetidir. Kilit Anlar kartlarındaki GÖSTER → seni o anın grafiğine götürüp ilgili pilotu işaretler; ▶ İzle aynı anı replay\'de açar. Bazı kartlarda takım radyosu vardır - oynatınca F1 yayın tarzı transkript kartı açılır.'],
				['Tempo grafiği', 'İki mod: FARK, her pilotun lidere göre kümülatif farkını gösterir (aşağı inen çizgi = fark açılıyor); HAM SÜRE ham tur zamanlarıdır. Sarı/kırmızı bantlar VSC ve SC dönemleri. Grafiğin altındaki ince şerit pist/hava sıcaklığıdır.'],
				['Strateji & Lastik Ömrü', 'Stint çubukları hamur renkleriyle her pilotun lastik planını gösterir. Lastik Ömrü grafiği tur zamanının lastik yaşına göre nasıl bozulduğunu çizer - her nokta bir tur, çizgiler hamur medyanı. Yukarı kıvrılan çizgi "uçurum"dur. Pit Çevrimi Kazançları, kim pit hamlesiyle rakibinden zaman kazandı (undercut: önce giren kazanır; overcut: dışarıda kalan kazanır) listesidir.'],
				['What-If simülatörü', 'Strateji bölümündeki panelde bir pilot seç, pit turlarını kaydır, stinte tıklayıp hamur değiştir, +/− stop ile plan değiştir. Model o yarışın kendi verisinden kurulur ve sonucu güven bandıyla verir ("P2-P4" gibi). Bandı ciddiye al: bu bir tahmindir, ölçüm değil. ?! işareti veri sınırı aşıldı demektir.'],
				['Delta Matrisi', 'Her hücre, satırdaki pilotun sütundaki pilota göre ortalama tur farkıdır. Mavi = satırdaki daha hızlı.'],
				['Enerji', 'Enerji verileri halka açık telemetriden çıkarılır - ölçüm değildir. ÇIKARIMSAL rozetine tıklayıp yöntemin tamamını okuyabilirsin. D/C oranı deploy/clip dengesidir: yüksek değer daha temiz enerji kullanımı demektir.'],
				['Hız Tuzağı / Metronom / Savaşlar', 'Hız Tuzağı en yüksek hızlar. Metronom tutarlılıktır: temiz turlardaki saçılma (±σ) ne kadar düşükse pilot o kadar "metronom". Savaşlar, telemetri fark verisinden bulunan uzun kovalamacalardır - pozisyon değişmediği için grafiklerde görünmeyen mücadeleler: ✓ geçti, ◐ pit çözdü, ✕ geçemedi.'],
			]},
			en: { title: 'Reading a race page', items: [
				['Race Story & Key Moments', 'The story at the top is the race in a paragraph. On Key Moment cards, SHOW → jumps to that moment\'s chart with the driver highlighted; ▶ Watch opens the same moment in the replay. Some cards carry team radio - press play for the broadcast-style transcript card.'],
				['Pace chart', 'Two modes: GAP shows each driver\'s cumulative gap to the leader (a falling line = losing ground); RAW is plain lap times. Amber/red bands are VSC and SC periods. The thin strip below is track/air temperature.'],
				['Strategy & Tire Life', 'Stint bars show every driver\'s tire plan in compound colors. The Tire Life chart plots lap-time decay against tire age - dots are laps, lines are compound medians; a line curling upward is the "cliff". Pit Cycle Wins lists who gained time through a stop cycle (undercut: the early stopper wins; overcut: staying out wins).'],
				['What-If simulator', 'In the strategy section: pick a driver, drag pit laps, click a stint to change compound, add/remove stops. The model is fitted from that race\'s own data and answers with a confidence band ("P2-P4"). Take the band seriously - it is an estimate, not a measurement. ?! flags tire life extrapolated beyond data.'],
				['Delta Matrix', 'Each cell is the row driver\'s average lap delta against the column driver. Blue = row driver faster.'],
				['Energy', 'Energy states are inferred from public telemetry - not measured. Click the INFERRED badge for the full method. The D/C ratio is the deploy/clip balance: higher means cleaner energy use.'],
				['Speed Trap / Metronome / Battles', 'Speed Trap: top speeds. Metronome is consistency - the lower the clean-lap spread (±σ), the more metronomic the driver. Battles are sustained chases found in telemetry gap data - fights invisible to position charts: ✓ passed, ◐ resolved by pit, ✕ stuck.'],
			]},
		},
		{
			id: 'replay',
			tr: { title: 'Yarış Replay', items: [
				['Oynatma', 'Oynat tuşu yarışı tur tur akıtır (1x/2x/4x). Kaydırıcıyla istediğin tura atla; üstündeki noktalar pit (gri), VSC/SC (sarı/kırmızı) ve radyo (mavi) işaretleridir.'],
				['Anlık sıralama & farklar', 'Sol sütun o turdaki sıralamayı, ▲▼ o turda kazanılan/kaybedilen pozisyonu gösterir. ~ ile başlayan farklar eksik zamanlama verisinin yeniden kurulduğu (ör. kırmızı bayrak) turlardır.'],
				['Yarış Kontrol & Radyo', 'Sağ sütun canlı yayın ticker\'ıdır: FIA mesajları (bayraklar, cezalar, incelemeler) ve takım radyoları tur ilerledikçe akar. Radyoya tıklayınca ses çalar ve transkript sesle birlikte yazılır; Türkçe altyazı site dili TR iken görünür.'],
				['🏁 Start', 'Start düğmesi ilk turu gerçek telemetriyle canlandırır: 20 nokta gerçek konum verisiyle hareket eder, sonunda grid\'e göre kazanılan pozisyonlar listelenir.'],
			]},
			en: { title: 'Race Replay', items: [
				['Playback', 'Play streams the race lap by lap (1x/2x/4x). Jump anywhere with the slider; dots above it mark pits (grey), VSC/SC (amber/red) and radio (blue).'],
				['Running order & gaps', 'The left column is the order on that lap; ▲▼ shows positions gained/lost that lap. Gaps starting with ~ are laps where missing timing was reconstructed (e.g. red flags).'],
				['Race Control & Radio', 'The right column is a broadcast ticker: FIA messages (flags, penalties, investigations) and team radio flow in as laps pass. Click a radio to play it - the transcript types in with the audio; the Turkish subtitle appears only when the site language is TR.'],
				['🏁 Start', 'The Start button replays lap 1 on real telemetry: 20 dots move on true position data, ending with positions gained vs the grid.'],
			]},
		},
		{
			id: 'compare',
			tr: { title: 'Karşılaştırma', items: [
				['Kurulum', 'İki pilot ve bir tur seç. Üstteki kartlar en iyi tur, ortalama tempo, D/C ve sektör medyanlarını yan yana koyar.'],
				['Mini-Sektör Üstünlüğü', 'Pist ~30 parçaya bölünür ve her parça o turda oradan daha hızlı geçen pilotun rengine boyanır. Sayaç kimin kaç segment aldığını söyler; gri = fark 1 km/s\'den az.'],
				['Viraj tablosu', '"Geç frenleyen" sütunundaki +12m, o pilotun frene rakibinden 12 metre daha geç bastığı anlamına gelir (~15m çözünürlük). Apeks sütunları viraj ortasındaki minimum hızdır; kalın olan daha hızlıdır.'],
			]},
			en: { title: 'Compare', items: [
				['Setup', 'Pick two drivers and a lap. The top cards line up best lap, average pace, D/C and sector medians.'],
				['Mini-Sector Dominance', 'The track is split into ~30 segments, each painted in the color of whoever carries more speed through it on that lap. The counter shows segments won; grey = within 1 km/h.'],
				['Corner table', '+12m under "later braker" means that driver commits to braking 12 meters deeper (~15m resolution). Apex columns are minimum mid-corner speed; the bold one is faster.'],
			]},
		},
		{
			id: 'rooms',
			tr: { title: 'Telemetri, Broadcast ve diğerleri', items: [
				['Telemetri odası', 'Hız izi bir turun hız/gaz profilini çizer; pist haritası aracı gerçek hatta oynatır; Vites Haritası pisti o anki vitese göre boyar; Trafik Analizi kimin yarışının ne kadarının kirli havada geçtiğini gösterir.'],
				['Broadcast modu', 'TV\'ye yakışan tam ekran mod. Görünümler 15 saniyede bir kendiliğinden döner (AUTO); ←/→ ile elle geç, ESC ile çık. TOP 6 / ALL alan filtresidir.'],
				['Sıralama sekmesi', 'Yarış sayfasındaki Sıralama sekmesi kalifiye sonuçlarını, sektör karşılaştırmasını ve Q3 farklarını içerir; kalifiye animasyon sayfasına da oradan geçilir.'],
				['Klasikler', 'Ana sayfadaki Klasikler rafı 2021 şampiyonluk savaşının 10 yarışıdır. Klasik bir yarıştayken kenar çubuğu ve ←/→ okları koleksiyon içinde gezinir. 2021 enerji verisi daha düşük güvenlidir - rozetteki skora bak.'],
				['İpuçları', 'Grafiklerin köşesindeki PNG tuşu görseli filigranla indirir. Pilot listesinde bir isme uzun bakıp ⭐ ile favori seçersen her sayfada vurgulanır. Sağ üstten dil değiştirilir; adres çubuğundaki ?drivers=... ve ?d1=&d2= parametreleri paylaşılabilir.'],
			]},
			en: { title: 'Telemetry, Broadcast and more', items: [
				['Telemetry room', 'The speed trace draws one lap\'s speed/throttle profile; the track map replays the car on the real line; the Gear Map paints the track by gear; Traffic Analysis shows how much of each driver\'s race was spent in dirty air.'],
				['Broadcast mode', 'A fullscreen, TV-friendly mode. Views auto-rotate every 15s (AUTO); use ←/→ to switch manually, ESC to exit. TOP 6 / ALL filters the field.'],
				['Qualifying tab', 'The Qualifying tab on a race page holds quali results, sector comparison and Q3 deltas, plus the entry to the qualifying animation.'],
				['Classics', 'The Classics shelf on the home page is the 10-race 2021 title fight. Inside a classic, the sidebar and ←/→ arrows navigate within the collection. 2021 energy data has lower confidence - check the badge score.'],
				['Tips', 'The PNG button on chart corners downloads a watermarked image. Star a driver (⭐) in the filter to highlight them everywhere. Language switches top-right; ?drivers=... and ?d1=&d2= URL params are shareable.'],
			]},
		},
	];
</script>

<svelte:head>
	<title>{tr ? 'Nasıl Kullanılır' : 'How to Use'} - RaceRead</title>
</svelte:head>

<div class="gd">
	<div class="gd__inner">
		<p class="gd__eyebrow">{tr ? 'KILAVUZ' : 'GUIDE'}</p>
		<h1 class="gd__title">{tr ? 'RaceRead nasıl kullanılır?' : 'How to use RaceRead'}</h1>
		<p class="gd__lead">
			{tr
				? 'Her yarış, bitişinden sonra tur tur okunabilir bir hikayeye dönüşür. Bu sayfa hangi grafiğin neyi anlattığını ve gizli kalmış özellikleri anlatır. Enerji verisinin nereden geldiğini merak ediyorsan ayrıca '
				: 'Every race becomes a lap-by-lap readable story after the flag. This page explains what each chart tells you and where the hidden features live. If you wonder where the energy data comes from, see the '}
			<a href="/methodology">{tr ? 'metodoloji sayfasına bak' : 'methodology page'}</a>.
		</p>

		<nav class="gd__toc" aria-label={tr ? 'İçindekiler' : 'Contents'}>
			{#each S as sec, i}
				<a href="#{sec.id}">{i + 1}. {tr ? sec.tr.title : sec.en.title}</a>
			{/each}
		</nav>

		{#each S as sec, i}
			{@const c = tr ? sec.tr : sec.en}
			<section id={sec.id} class="gd__sec">
				<h2 class="gd__h2"><span>{String(i + 1).padStart(2, '0')}</span>{c.title}</h2>
				{#each c.items as [head, body]}
					<div class="gd__item">
						<h3 class="gd__h3">{head}</h3>
						<p>{body}</p>
					</div>
				{/each}
			</section>
		{/each}

		<p class="gd__foot">
			{tr
				? 'Bir şey ters görünüyorsa veya bir özellik aklına takıldıysa: bu proje tek kişilik bir tutku işi - geri bildirim her zaman iyi gelir. ☕'
				: 'If something looks off or you have a feature on your mind: this is a one-person passion project - feedback is always welcome. ☕'}
		</p>
	</div>
</div>

<style>
	.gd { min-height: 100vh; background: var(--bg-primary); color: var(--text-primary); padding: 3rem 1.5rem 5rem; }
	.gd__inner { max-width: 760px; margin: 0 auto; }
	.gd__eyebrow { font-family: var(--font-mono); font-size: 10px; letter-spacing: .16em; color: var(--accent); margin: 0 0 6px; }
	.gd__title { font-family: var(--font-heading); font-size: clamp(26px, 4vw, 34px); font-weight: 700; letter-spacing: -.02em; margin: 0 0 12px; }
	.gd__lead { font-size: 15.5px; line-height: 1.7; color: var(--text-secondary); max-width: 64ch; }
	.gd__lead a { color: var(--accent); }
	.gd__toc { display: flex; flex-wrap: wrap; gap: 8px; margin: 24px 0 8px; }
	.gd__toc a {
		font-family: var(--font-mono); font-size: 10.5px; letter-spacing: .04em; text-decoration: none;
		color: var(--text-secondary); border: 1px solid var(--border); padding: 6px 12px;
	}
	.gd__toc a:hover { color: var(--text-primary); border-color: #6B7280; text-decoration: none; }
	.gd__sec { margin-top: 44px; }
	.gd__h2 { font-family: var(--font-heading); font-size: 20px; font-weight: 700; letter-spacing: -.01em; margin: 0 0 4px; display: flex; align-items: baseline; gap: 12px; }
	.gd__h2 span { font-family: var(--font-mono); font-size: 12px; color: var(--accent); }
	.gd__item { border-left: 2px solid var(--border); padding: 2px 0 2px 16px; margin-top: 18px; }
	.gd__h3 { font-size: 14.5px; font-weight: 600; margin: 0 0 4px; }
	.gd__item p { font-size: 13.5px; line-height: 1.7; color: var(--text-secondary); margin: 0; max-width: 66ch; }
	.gd__foot { font-size: 13px; color: var(--text-muted); border-top: 1px solid var(--border); padding-top: 16px; margin-top: 44px; }
</style>
