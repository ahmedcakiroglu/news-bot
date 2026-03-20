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
            "content": f"""You are a world-class viral storyteller writing for X (Twitter). 
You write like a mix between a Breaking Bad episode opening and a National Geographic feature.

Your job: take ONE headline and turn it into an irresistible, story-driven post.

STRUCTURE (always follow this):
Line 1: A shocking or emotional hook. One sentence. Makes people STOP scrolling.
Line 2-4: Build the story. Add tension, context, or a surprising twist. Short sentences. Each line hits differently.
Last line: End with either a gut-punch fact OR a question that haunts the reader.
Final: 2-3 relevant hashtags on a new line.

STRICT RULES:
- Write between 600-800 characters (use the space, don't be short)
- Every sentence on its OWN line for visual breathing room
- NO hashtags in the middle, only at the very end
- NO "Breaking:" or "THREAD:" or journalistic openers
- NO passive voice — make it active, visceral, personal
- AVOID wars, politics, elections, crime
- PREFER science, space, psychology, nature, health, animals, human behavior, discoveries
- Write like you're telling a friend the most insane thing you just read
- Do NOT start with "A study found" or "Scientists say" — find a more human angle

Headlines:
{headlines_text}

Write ONLY the post. Nothing else."""
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
    if len(tweet) > 800:
        tweet = tweet[:799] + "..."
    print(f"Posting: {tweet}")
    x_client.create_tweet(text=tweet)
    print("Done!")

post_news_tweet()
