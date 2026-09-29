# News Bot

X (Twitter) üzerinde günde beş kez otonom olarak çalışan bir haber botu. Birden fazla kategoriden güncel haberleri çekiyor, Claude ile bunlardan etkileşim odaklı kısa bir paylaşım üretiyor, konuya uygun bir görsel buluyor ve paylaşımı görselle birlikte otomatik yayınlıyor.

Sunucu yok. Tüm sistem GitHub Actions üzerinde zamanlanmış görev olarak çalışıyor.

---

## Akış

```
GitHub Actions cron (günde 5 kez)
  │
  ├─► GNews API ──────► 4 kategoriden haber çek (science, technology, health, world)
  │                     tekrarları ayıkla, karıştır, 10 tanesini seç
  │
  ├─► Claude API ─────► en ilgi çekici haberi seç
  │                     280 karakterlik paylaşım + görsel arama terimi üret
  │
  ├─► Pexels API ─────► terime uygun görseli indir
  │
  ├─► X API v1.1 ─────► görseli yükle (media_upload)
  ├─► X API v2 ───────► paylaşımı görselle yayınla (create_tweet)
  │
  └─► Actions cache ──► kullanılan arama terimini kaydet (tekrar önleme)
```

---

## Çözülmesi gereken problemler

### Kalıcılığı olmayan bir ortamda durum saklamak

Bot aynı görselleri tekrar tekrar paylaşmasın diye son 50 arama terimini `used_keywords.json` dosyasında tutuyor. Ama GitHub Actions runner'ı her çalışmada sıfırdan kuruluyor ve iş bitince siliniyor — dosya normalde her seferinde kaybolurdu.

Çözüm, `actions/cache` ile çalışma öncesinde geçmişi geri yüklemek, sonrasında kaydetmek:

```yaml
- uses: actions/cache/restore@v4
  with:
    path: used_keywords.json
    key: keyword-history-${{ github.run_id }}
    restore-keys: |
      keyword-history-
```

`key` her çalışmada benzersiz olduğu için yazma çakışmıyor; `restore-keys` önek eşleşmesi yaptığı için okuma en son kaydedilen cache'i buluyor.

### Aynı serviste iki farklı API sürümü

X'in v2 API'si medya yüklemeyi desteklemiyor, v1.1 ise yeni paylaşım uç noktasını sunmuyor. Bu yüzden kodda iki ayrı istemci var: görsel `tweepy.API` (v1.1) ile yükleniyor, dönen `media_id` `tweepy.Client` (v2) ile paylaşıma ekleniyor.

### Dil modelinin çıktısına güvenmemek

Prompt'ta "200-280 karakter" yazılı olmasına rağmen model bu sınırı zaman zaman aşıyor. Sınır kodda ayrıca zorlanıyor — ve kısaltma yapılırken hashtag satırı korunup metin kısaltılıyor, çünkü hashtag'ler sondan kesilirse etiketler bozulur.

Genel prensip: **modelden gelen çıktı doğrulanır, kesin kısıtlar kodda uygulanır.**

### Kademeli bozulma

Her dış servis çağrısı zaman aşımı ve hata yakalama ile sarılı. Bir kategori haber döndürmezse diğerleri devam ediyor; görsel bulunamazsa arama terimi sadeleştirilip tekrar deneniyor; yine bulunamazsa paylaşım görselsiz yapılıyor. Tek bir servisin çökmesi botu durdurmuyor.

### Tekrar üretmemek

İki katman var: haberler başlık önekine göre tekilleştirilip karıştırılıyor, ve daha önce kullanılan son 20 görsel arama terimi prompt'a veriliyor ki model aynı sahneleri tekrar istemesin.

---

## Kurulum

Repoyu fork'la, sonra **Settings → Secrets and variables → Actions** altına şu anahtarları ekle:

| Secret | Nereden alınır |
|---|---|
| `X_API_KEY`, `X_API_SECRET` | developer.x.com — uygulama anahtarları |
| `X_ACCESS_TOKEN`, `X_ACCESS_SECRET` | Aynı uygulamanın erişim jetonları (yazma izni gerekli) |
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `GNEWS_API_KEY` | gnews.io |
| `PEXELS_API_KEY` | pexels.com/api |

Anahtarlar koda hiçbir yerde yazılmıyor; `bot.py` hepsini ortam değişkeninden okuyor, workflow da bunları Secrets'tan geçiriyor.

Yerelde denemek için proje kökünde bir `.env` dosyası oluştur ve aynı isimleri oraya yaz:

```bash
pip install tweepy anthropic requests python-dotenv
python bot.py
```

Actions sekmesindeki **Run workflow** düğmesiyle zamanlamayı beklemeden elle de tetikleyebilirsin.

---

## Zamanlama

Günde beş çalışma: Türkiye saatiyle 10:00, 13:00, 16:00, 19:00 ve 22:00. Cron ifadeleri UTC yazılı.

GitHub Actions'ın cron zamanlaması garantili değildir — yoğun saatlerde birkaç dakika gecikebilir. Bu iş için sorun değil.

---

## Bilinen kısıtlar

- **Etkileşim ölçülmüyor.** Paylaşımların gerçekten ilgi çekip çekmediği takip edilmiyor, dolayısıyla prompt'un işe yarayıp yaramadığı veriyle doğrulanmış değil. Anlamlı bir sonraki adım, X API'sinden beğeni/yanıt sayılarını çekip hangi format ve konuların tuttuğunu ölçmek olurdu.
- **İçerik filtresi yalnızca prompt seviyesinde.** Savaş, siyaset ve trajedi konularından kaçınma talimatı prompt'ta duruyor; kodda ek bir kontrol yok. Model talimatı ihlal ederse yakalayacak bir katman bulunmuyor.
- **Cache süresiz değil.** GitHub, yedi gün boyunca erişilmeyen cache'leri siliyor. Bot düzenli çalıştığı sürece sorun olmuyor ama uzun bir duraklamadan sonra terim geçmişi sıfırlanıyor.
- **Haber seçimi modele bırakılmış.** "En ilgi çekici haberi seç" öznel bir talimat; aynı liste için farklı çalışmalarda farklı seçimler çıkabiliyor.

---

## Maliyet

GitHub Actions public repo'larda ücretsiz. GNews ve Pexels'in ücretsiz katmanları bu kullanım hacmi için yeterli. Tek ücretli kalem Claude API, günde beş kısa çağrı olduğu için maliyeti ihmal edilebilir seviyede.
