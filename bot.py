import tweepy
import anthropic
import requests
import os
import tempfile
from dotenv import load_dotenv

load_dotenv()

# --- Connect to X (v1.1 for media upload) ---
auth = tweepy.OAuth1UserHandler(
    os.getenv("X_API_KEY"),
    os.getenv("X_API_SECRET"),
    os.getenv("X_ACCESS_TOKEN"),
    os.getenv("X_ACCESS_SECRET")
)
api_v1 = tweepy.API(auth)

# --- Connect to X (v2 for tweeting) ---
x_client = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# --- Get News ---
def get_news():
    url = "https://gnews.io/api/v4/top-headlines"
    response = requests.get(url, params={
        "token": os.getenv("GNEWS_API_KEY"),
        "lang": "en",
        "max": 8
    }).json()
    articles = []
    for a in response.get("articles", []):
        if a.get("title") and a.get("description"):
            articles.append(f"{a['title']}: {a['description']}")
    return articles[:8]

# --- Generate Tweet + Image Keyword ---
def generate_tweet_and_keyword(headlines):
    headlines_text = "\n".join(f"- {h}" for h in headlines)
    message = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""You are a world-class viral storyteller writing for X (Twitter).

Write ONE story-driven post AND a photo search keyword.

STRUCTURE:
Line 1: A shocking or emotional hook.
Line 2-4: Build the story with tension and a surprising twist.
Last line: A gut-punch fact OR haunting question.
Hashtags: 2-3 on a new line at the end.

RULES:
- Write between 600-800 characters
- Every sentence on its OWN line
- AVOID wars, politics, elections, crime
- PREFER science, space, psychology, nature, health, animals, discoveries
- Write like telling a friend the most insane thing you just read

After the post, on a completely new line write:
KEYWORD: [one simple English word for a photo, e.g. ocean, brain, space, dolphin]

Headlines:
{headlines_text}

Write ONLY the post and keyword. Nothing else."""
        }]
    )
    full = message.content[0].text.strip()
    
    if "KEYWORD:" in full:
        parts = full.split("KEYWORD:")
        tweet = parts[0].strip()
        keyword = parts[1].strip().split()[0]
    else:
        tweet = full
        keyword = "nature"
    
    return tweet, keyword

# --- Get Image from Pexels ---
def get_image(keyword):
    headers = {"Authorization": os.getenv("PEXELS_API_KEY")}
    response = requests.get(
        "https://api.pexels.com/v1/search",
        headers=headers,
        params={"query": keyword, "per_page": 1, "orientation": "landscape"}
    ).json()
    
    photos = response.get("photos", [])
    if not photos:
        return None
    
    image_url = photos[0]["src"]["large"]
    image_data = requests.get(image_url).content
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
        f.write(image_data)
        return f.name

# --- Post Tweet with Image ---
def post_news_tweet():
    print("Fetching news...")
    headlines = get_news()
    if not headlines:
        print("No news found.")
        return
    
    print("Generating tweet...")
    tweet, keyword = generate_tweet_and_keyword(headlines)
    
    if len(tweet) > 800:
        tweet = tweet[:799] + "..."
    
    print(f"Keyword: {keyword}")
    print(f"Tweet: {tweet}")
    
    print("Getting image...")
    image_path = get_image(keyword)
    
    if image_path:
        print("Uploading image...")
        media = api_v1.media_upload(filename=image_path)
        x_client.create_tweet(text=tweet, media_ids=[media.media_id])
        os.unlink(image_path)
    else:
        print("No image found, posting without image...")
        x_client.create_tweet(text=tweet)
    
    print("Done!")

post_news_tweet()
