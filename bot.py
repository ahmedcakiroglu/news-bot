import tweepy
import anthropic
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# --- Connect to X ---
x_client = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

# --- Connect to Claude ---
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# --- Get News ---
def get_news():
    url = "https://gnews.io/api/v4/top-headlines"
    response = requests.get(url, params={
        "token": os.getenv("GNEWS_API_KEY"),
        "lang": "en",
        "max": 8
    }).json()
    print("GNews response:", response)

    articles = []
    for a in response.get("articles", []):
        if a.get("title") and a.get("description"):
            articles.append(f"{a['title']}: {a['description']}")
    return articles[:8]

# --- Generate Tweet ---
def generate_tweet(headlines):
    headlines_text = "\n".join(f"- {h}" for h in headlines)
    message = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": f"""You are a magazine-style viral news writer for X (Twitter).

Write ONE long, story-driven tweet (max 280 chars) based on the most surprising, emotional, or mind-blowing headline below.

Rules:
- AVOID wars, politics, elections
- PREFER science, space, health, nature, weird facts, human interest
- Hook in the first line — make it impossible NOT to read
- Build like a story: setup → twist → emotional gut punch
- End with a question that makes people stop and think
- Add 2-3 hashtags at the very end
- Write ONLY the tweet, nothing else, no quotation marks

Headlines:
{headlines_text}"""
        }]
    )
    return message.content[0].text.strip()

# --- Main Function ---
def post_news_tweet():
    print("Fetching news...")
    headlines = get_news()
    if not headlines:
        print("No news found.")
        return
    print("Generating tweet...")
    tweet = generate_tweet(headlines)
    if len(tweet) > 400:
        tweet = tweet[:399] + "..."
    print(f"Posting: {tweet}")
    x_client.create_tweet(text=tweet)
    print("Done!")

post_news_tweet()
