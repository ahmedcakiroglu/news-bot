import tweepy
import anthropic
import requests
import os
import json
import random
import tempfile
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# X (Twitter) API Bağlantıları
# ============================================================

auth = tweepy.OAuth1UserHandler(
    os.getenv("X_API_KEY"),
    os.getenv("X_API_SECRET"),
    os.getenv("X_ACCESS_TOKEN"),
    os.getenv("X_ACCESS_SECRET")
)
api_v1 = tweepy.API(auth)

x_client = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ============================================================
# Kullanılmış Keyword Geçmişi (Tekrar Önleme)
# ============================================================

HISTORY_FILE = "used_keywords.json"

def load_keyword_history():
    """Daha önce kullanılan keyword'leri yükle."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_keyword_history(history):
    """Keyword geçmişini kaydet. Son 50 tanesini tut."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[-50:], f)

# ============================================================
# İYİLEŞTİRME 1: Daha İyi Haber Kaynağı
# ============================================================

# İlgi çekici kategoriler — sıkıcı genel haberlerden kaçınmak için
TOPICS = ["science", "technology", "health", "world"]

def get_news():
    """Birden fazla kategoriden haber çek ve en ilginçlerini seç."""
    all_articles = []

    for topic in TOPICS:
        try:
            url = "https://gnews.io/api/v4/top-headlines"
            response = requests.get(url, params={
                "token": os.getenv("GNEWS_API_KEY"),
                "lang": "en",
                "topic": topic,
                "max": 5
            }, timeout=10).json()

            for a in response.get("articles", []):
                title = a.get("title", "")
                desc = a.get("description", "")
                if title and desc:
                    all_articles.append({
                        "text": f"{title}: {desc}",
                        "topic": topic,
                        "url": a.get("url", "")
                    })
        except Exception as e:
            print(f"  [{topic}] haber çekilemedi: {e}")

    # Tekrarları kaldır ve karıştır
    seen_titles = set()
    unique = []
    for art in all_articles:
        short_title = art["text"][:60]
        if short_title not in seen_titles:
            seen_titles.add(short_title)
            unique.append(art)

    random.shuffle(unique)
    selected = unique[:10]

    print(f"  Toplam {len(all_articles)} haber bulundu, {len(selected)} tanesi seçildi.")
    return selected

# ============================================================
# İYİLEŞTİRME 3: Etkileşim Odaklı Tweet Üretimi
# ============================================================

def generate_tweet_and_keyword(articles, used_keywords):
    """Claude ile kısa, vurucu, etkileşim odaklı tweet üret."""
    headlines_text = "\n".join(f"- [{a['topic']}] {a['text']}" for a in articles)
    used_kw_text = ", ".join(used_keywords[-20:]) if used_keywords else "yok"

    message = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": f"""You are a viral science/nature storyteller on X (Twitter).

TASK: Pick the MOST fascinating headline below and write a short, punchy post.

FORMAT (follow this EXACTLY):
Line 1: A jaw-dropping hook that stops the scroll (use an emoji at the start)
Line 2-3: The surprising story in 1-2 SHORT sentences
Line 4: End with a thought-provoking question OR a mind-blowing fact
Line 5: 2-3 relevant hashtags

STRICT RULES:
- Total length: 200-280 characters (this is CRITICAL for engagement)
- Every sentence on its OWN line
- Use 1-2 emojis max (at hook and/or ending)
- NEVER write about wars, politics, elections, crime, or tragedy
- PICK science, space, psychology, nature, health, animals, ocean, discoveries
- Tone: excited friend telling you something incredible
- End with a question to drive replies

After the post, write on a new line:
KEYWORD: [2-3 word specific scene description for a photo, e.g. "deep ocean jellyfish", "aurora borealis night", "neuron microscope close"]

PREVIOUSLY USED KEYWORDS (avoid these): {used_kw_text}

Headlines:
{headlines_text}

Write ONLY the post and keyword line. Nothing else."""
        }]
    )
    full = message.content[0].text.strip()

    if "KEYWORD:" in full:
        parts = full.split("KEYWORD:")
        tweet = parts[0].strip()
        keyword = parts[1].strip().strip('"').strip("'")
    else:
        tweet = full
        keyword = "stunning nature landscape"

    return tweet, keyword

# ============================================================
# İYİLEŞTİRME 2: Görsel Çeşitliliği
# ============================================================

def get_image(keyword, used_keywords):
    """Pexels'ten rastgele, çeşitli görseller çek."""
    headers = {"Authorization": os.getenv("PEXELS_API_KEY")}

    # Farklı sayfa ve sonuçlardan rastgele seç
    random_page = random.randint(1, 3)

    try:
        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers=headers,
            params={
                "query": keyword,
                "per_page": 15,
                "page": random_page,
                "orientation": "landscape",
                "size": "large"
            },
            timeout=10
        ).json()
    except Exception as e:
        print(f"  Pexels API hatası: {e}")
        return None

    photos = response.get("photos", [])
    if not photos:
        # Keyword çok spesifik olabilir, basitleştirip tekrar dene
        simple_keyword = keyword.split()[0] if " " in keyword else keyword
        print(f"  '{keyword}' için görsel bulunamadı, '{simple_keyword}' deneniyor...")
        try:
            response = requests.get(
                "https://api.pexels.com/v1/search",
                headers=headers,
                params={
                    "query": simple_keyword,
                    "per_page": 15,
                    "orientation": "landscape"
                },
                timeout=10
            ).json()
            photos = response.get("photos", [])
        except Exception:
            return None

    if not photos:
        return None

    # Rastgele bir fotoğraf seç
    chosen = random.choice(photos)
    image_url = chosen["src"]["large2x"]  # Daha yüksek kalite
    photographer = chosen.get("photographer", "Unknown")

    print(f"  Görsel seçildi: {photographer} tarafından (ID: {chosen['id']})")

    try:
        image_data = requests.get(image_url, timeout=15).content
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(image_data)
            return f.name
    except Exception as e:
        print(f"  Görsel indirme hatası: {e}")
        return None

# ============================================================
# Ana Fonksiyon
# ============================================================

def post_news_tweet():
    print(f"\n{'='*50}")
    print(f"Bot çalışıyor — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    # Keyword geçmişini yükle
    used_keywords = load_keyword_history()

    # 1. Haberleri çek
    print("\n[1/4] Haberler çekiliyor...")
    articles = get_news()
    if not articles:
        print("Haber bulunamadı!")
        return

    # 2. Tweet üret
    print("\n[2/4] Tweet üretiliyor...")
    tweet, keyword = generate_tweet_and_keyword(articles, used_keywords)

    # Karakter limiti kontrolü
    if len(tweet) > 280:
        print(f"  Uyarı: Tweet {len(tweet)} karakter, kısaltılıyor...")
        # Hashtag'leri koru, metni kısalt
        lines = tweet.split("\n")
        hashtag_line = ""
        content_lines = []
        for line in lines:
            if line.strip().startswith("#"):
                hashtag_line = line.strip()
            else:
                content_lines.append(line)

        content = "\n".join(content_lines)
        max_content = 280 - len(hashtag_line) - 2  # \n + boşluk
        if len(content) > max_content:
            content = content[:max_content - 3] + "..."
        tweet = f"{content}\n{hashtag_line}" if hashtag_line else content

    print(f"  Keyword: {keyword}")
    print(f"  Tweet ({len(tweet)} karakter):\n  {tweet}")

    # 3. Görsel al
    print("\n[3/4] Görsel aranıyor...")
    image_path = get_image(keyword, used_keywords)

    # 4. Tweet'i paylaş
    print("\n[4/4] Tweet paylaşılıyor...")
    try:
        if image_path:
            media = api_v1.media_upload(filename=image_path)
            x_client.create_tweet(text=tweet, media_ids=[media.media_id])
            os.unlink(image_path)
            print("  Tweet görsel ile paylaşıldı!")
        else:
            x_client.create_tweet(text=tweet)
            print("  Tweet görselsiz paylaşıldı.")
    except Exception as e:
        print(f"  Tweet paylaşma hatası: {e}")
        if image_path and os.path.exists(image_path):
            os.unlink(image_path)
        return

    # Keyword geçmişini güncelle
    used_keywords.append(keyword)
    save_keyword_history(used_keywords)

    print(f"\n{'='*50}")
    print("Tamamlandı!")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    post_news_tweet()
