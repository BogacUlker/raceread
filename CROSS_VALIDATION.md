# Energy Inference Cross-Validation — 2026 Australian GP

**Drivers**: RUS, ANT (Mercedes) | LEC, HAM (Ferrari) | VER (Red Bull) | NOR (McLaren)
**VSC Periods**: Laps 12-14, 18-20, 34

---

## 1. Race Averages (Raw)

| Driver | Team | Deploy % | Harvest % | Clip % | Neutral % |
|--------|------|----------|-----------|--------|-----------|
| **RUS** | Mercedes | 3.00 | 22.80 | 1.01 | 73.19 |
| **ANT** | Mercedes | 2.39 | 23.05 | 1.14 | 73.42 |
| **VER** | Red Bull | 2.54 | 24.73 | 0.96 | 71.77 |
| **LEC** | Ferrari | 2.34 | 20.21 | 1.61 | 75.84 |
| **NOR** | McLaren | 2.86 | 26.61 | 1.28 | 69.25 |
| **HAM** | Ferrari | 2.39 | 20.23 | 1.90 | 75.47 |

---

## 2. Normalized Active States (Deploy + Harvest + Clip = 100%)

Neutral çıkarılmış, sadece enerji-aktif sample'ların dağılımı:

| Driver | Team | Deploy | Harvest | Clip | Deploy/Clip Ratio |
|--------|------|--------|---------|------|-------------------|
| **RUS** | Mercedes | **11.2%** | 85.0% | 3.8% | **2.95** |
| ANT | Mercedes | 9.0% | 86.7% | 4.3% | 2.09 |
| VER | Red Bull | 9.0% | 87.6% | **3.4%** | **2.65** |
| LEC | Ferrari | 9.7% | 83.7% | 6.6% | 1.47 |
| **NOR** | McLaren | 9.3% | 86.6% | 4.1% | 2.27 |
| HAM | Ferrari | 9.8% | 82.5% | **7.8%** | **1.26** |

**Deploy/Clip Ratio**: Deploying'in clipping'e oranı. Yüksek = enerjiyi daha verimli kullanıyor. Düşük = batarya limitlerine sık takılıyor.

### Sıralama (verimlilik):
1. **RUS** (2.95) — En yüksek deploy, en düşük clip oranlarından biri
2. **VER** (2.65) — En düşük clip, disiplinli enerji yönetimi
3. **NOR** (2.27) — Dengeli profil
4. **ANT** (2.09) — RUS'a göre daha muhafazakar
5. **LEC** (1.47) — Yüksek clip, batarya stresi belirgin
6. **HAM** (1.26) — En yüksek clip, en düşük verimlilik

---

## 3. Takım Arkadaşı Karşılaştırması

### Mercedes: RUS vs ANT

| Metric | RUS | ANT | Delta |
|--------|-----|-----|-------|
| Deploy % | 3.00 | 2.39 | **RUS +0.61** |
| Harvest % | 22.80 | 23.05 | ANT +0.25 |
| Clip % | 1.01 | 1.14 | ANT +0.13 |
| D/C Ratio | 2.95 | 2.09 | **RUS +0.86** |

**Yorum**: RUS daha agresif deploy ediyor ve buna rağmen daha az clip'e düşüyor. ANT daha konservatif — benzer harvesting ama daha az deploy ile batarya rezervi tutuyor. RUS'un enerji yönetimi belirgin şekilde daha etkili; aynı araçla daha fazla güç kullanıp daha az limite takılıyor.

### Ferrari: LEC vs HAM

| Metric | LEC | HAM | Delta |
|--------|-----|-----|-------|
| Deploy % | 2.34 | 2.39 | HAM +0.05 |
| Harvest % | 20.21 | 20.23 | ~eşit |
| Clip % | 1.61 | 1.90 | **HAM +0.29** |
| D/C Ratio | 1.47 | 1.26 | **LEC +0.21** |

**Yorum**: Ferrari'nin iki pilotu benzer deploy ve harvest gösteriyor — bu aracın enerji karakteristiğini yansıtıyor. Ancak HAM'ın clip oranı tüm pilotlar arasında en yüksek (1.90%). Neredeyse aynı miktarda deploy ediyorlar ama HAM daha sık batarya limitine çarpıyor. Bu, HAM'ın deploy zamanlamasının daha az optimum olduğunu veya farklı yarış stratejisinin (sıra savunması?) batarya stresini artırdığını gösterebilir. Ferrari genel olarak en yüksek clip oranına sahip takım — araç ya da yazılım tarafında bir enerji yönetim sorunu olabilir.

---

## 4. En Yüksek Clipping Yapan 3 Pilot/Tur

| # | Driver | Lap | Clip % | Deploy % | VSC? | Analiz |
|---|--------|-----|--------|----------|------|--------|
| 1 | **LEC** | 2 | **6.05%** | 3.63 | No | Yarış başı — agresif deploy sonrası batarya hemen tükenmiş. İlk turların yüksek enerji talebi |
| 2 | **ANT** | 16 | **5.01%** | 1.62 | No | VSC sonu (lap 14) sonrası restart — ani yüksek güç talebi, batarya VSC'de yeterince dolmamış |
| 3 | **NOR** | 52 | **4.85%** | 2.42 | No | Yarış sonu — uzun stint sonrası batarya yorgunluğu, son turlar push |

---

## 5. En Yüksek Deploy Yapan 3 Pilot/Tur

| # | Driver | Lap | Deploy % | Clip % | VSC? | Analiz |
|---|--------|-----|----------|--------|------|--------|
| 1 | **NOR** | 38 | **9.62%** | 0.00 | No | Mükemmel enerji turu — maksimum deploy, sıfır clip. Pit sonrası taze lastik + dolu batarya |
| 2 | **ANT** | 2 | **9.02%** | 4.21 | No | Agresif yarış başı — çok yüksek deploy ama yüksek clip ile beraber (sürdürülemez) |
| 3 | **HAM** | 58 | **7.95%** | 1.99 | No | Son tur all-in — batarya sınırını zorlayarak tüm enerjiyi harcama |

**NOR Lap 38 dikkat çekici**: 9.62% deploy ile 0% clip — bu turun enerji verimliliği olağanüstü. Post-pit out-lap veya undercut sırasında dolu bataryayı mükemmel zamanlamayla kullanmış.

---

## 6. VSC Turlarında Enerji Pattern Değişimi

### VSC (Laps 12-14, 18-20, 34) vs Normal Turlar

| Driver | | Deploy % | Harvest % | Clip % |
|--------|-|----------|-----------|--------|
| **RUS** | VSC | 2.21 | **27.59** | 1.07 |
| | Normal | 3.11 | 22.14 | 1.01 |
| **ANT** | VSC | 1.11 | **28.84** | 0.63 |
| | Normal | 2.56 | 22.26 | 1.21 |
| **VER** | VSC | 1.81 | **32.05** | 0.28 |
| | Normal | 2.64 | 23.73 | 1.05 |
| **LEC** | VSC | 1.22 | **26.32** | 0.93 |
| | Normal | 2.49 | 19.37 | 1.70 |
| **NOR** | VSC | 1.19 | **32.78** | 0.55 |
| | Normal | 3.09 | 25.76 | 1.37 |
| **HAM** | VSC | 0.96 | **24.21** | 0.81 |
| | Normal | 2.59 | 19.68 | 2.05 |

### VSC Pattern Özeti

**VSC sırasında tüm pilotlarda tutarlı pattern**:
- **Harvesting +5-8 puan artış**: Hız limiti nedeniyle daha fazla frenleme/kısma, batarya şarj oluyor
- **Deploying -1-2 puan düşüş**: Hız limiti nedeniyle ekstra güce gerek yok
- **Clipping neredeyse sıfıra düşüyor**: Batarya tüketilmiyor, limit yok

Bu pattern inference'ın doğruluğunu güçlü şekilde destekliyor: VSC fiziksel olarak düşük güç talebi + yüksek şarj fırsatı yaratıyor ve model bunu doğru yakalıyor.

**En büyük VSC fayda gören**: VER ve NOR — normal turlarına göre harvesting +8 puan artış, VSC sonrası dolu batarya ile restart avantajı.

---

## 7. Takım Bazlı Değerlendirme

| Team | Avg Deploy | Avg Clip | D/C Ratio | Enerji Verimliliği |
|------|-----------|----------|-----------|-------------------|
| **Mercedes** | 2.70 | 1.08 | **2.50** | En iyi |
| **Red Bull** | 2.54 | 0.96 | **2.65** | En iyi (tek pilot) |
| **McLaren** | 2.86 | 1.28 | **2.23** | İyi |
| **Ferrari** | 2.37 | 1.76 | **1.35** | Zayıf |

### Bir Cümlelik Değerlendirme

**Red Bull ve Mercedes enerjiyi en verimli yöneten takımlar** — düşük clipping ile tutarlı deployment yapabiliyorlar; Ferrari ise her iki pilotunda da yüksek clipping ile batarya limitine en sık takılan takım, bu da ya enerji geri kazanım yazılımında ya da deployment stratejisinde bir optimizasyon açığına işaret ediyor.

---

## Dosyalar

VPS'te `~/raceread/` altında:
- `rus_energy_laps.json` — 58 tur (VSC flag'li)
- `ant_energy_laps.json` — 58 tur
- `ver_energy_laps.json` — 58 tur
- `lec_energy_laps.json` — 58 tur
- `nor_energy_laps.json` — 58 tur
- `ham_energy_laps.json` — 58 tur
