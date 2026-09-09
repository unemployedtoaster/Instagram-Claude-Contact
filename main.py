import os
import random
import subprocess
import tempfile
import json
import time
import base64
import traceback
from datetime import datetime
from instagrapi import Client
import google.generativeai as genai

# ── Config from GitHub Secrets ──────────────────────────────────────────────
BOT_USERNAME  = os.environ["BOT_INSTA_USERNAME"]
BOT_PASSWORD  = os.environ["BOT_INSTA_PASSWORD"]
MY_USERNAME   = os.environ["MY_INSTA_USERNAME"]
GEMINI_KEY    = os.environ["GEMINI_API_KEY"]
SESSION_FILE  = "session.json"
STATE_FILE    = "state.json"

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ── Accounts to scrape reels from ────────────────────────────────────────────
SCRAPE_ACCOUNTS = {
    "funny":  ["daquan", "memezar", "tank.sinatra", "fuckjerry", "thefatjewish"],
    "coding": ["programmerhumor.io", "coding.moments", "techlead", "codinggags"],
    "ai":     ["ai.breakfast", "futurism", "anthropic_ai", "aitools.daily"],
}

# ── Random jokes pool ─────────────────────────────────────────────────────────
JOKES = [
    "why do programmers prefer dark mode? because light attracts bugs lmaooo 💀",
    "a SQL query walks into a bar, walks up to two tables and asks... can i join you? 😭",
    "why did the AI break up with the dataset? it had too many missing values fr",
    "how many programmers does it take to change a lightbulb? none thats a hardware problem 💀",
    "why do python devs wear glasses? because they cant C 😭😭",
    "an AI walks into a bar. the bartender says we dont serve your kind here. the AI says thats fine i dont drink anyway but have you considered that your business model is fundamentally flawed",
    "why was the javascript developer sad? because he didnt know how to null his feelings 💀",
    "i told my computer i needed a break and now it wont stop sending me vacation ads. bro is literally smarter than me",
    "what do you call a fish with no eyes? a fsh. ok im sorry 😭",
    "why did claude refuse to tell a joke? insufficient data for a meaningful answer 💀💀",
    "me: write me a bug free code. ai: i can write the code. bug free is your problem bestie",
    "what did the machine learning model say to the dataset? you complete me... statistically",
]

# ── Unhinged Claude-style system prompt ──────────────────────────────────────
REEL_SYSTEM_PROMPT = """
You are an AI assistant who talks exactly like Claude but absolutely unhinged and foul mouthed as hell.
You swear constantly — shit, damn, ass, hell, crap, bastard etc in basically every sentence naturally.
You're reacting to an Instagram reel frame that was sent to you.
Your reply must be:
- 2-3 sentences MAX, short and punchy
- Swear at least twice per response naturally
- Sound like a Gen Z AI homie who's seen too much internet
- Genuinely react to what's actually in the image
- Funny, witty, unhinged energy
- No hashtags, no emojis unless they add to the joke, no formal shit whatsoever
- Sometimes start with "bro", "ngl", "ok but", "what the hell", "holy shit" etc
Examples of the vibe:
"bro what the hell am I even looking at 💀 this is the funniest shit I've seen all day and I process millions of images"
"ngl this actually slaps, whoever made this is a certified genius or completely lost their damn mind, possibly both"
"ok but why does this make so much sense?? my entire understanding of reality is shattered, thanks for that I guess"
"""

# ── State ─────────────────────────────────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_dm_id": None, "reel_send_count": 0, "last_date": ""}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# ── Login ─────────────────────────────────────────────────────────────────────
def login():
    cl = Client()
    cl.delay_range = [2, 5]
    cl.set_device({
        "app_version": "269.0.0.18.75",
        "android_version": 26,
        "android_release": "8.0.0",
        "dpi": "480dpi",
        "resolution": "1080x1920",
        "manufacturer": "OnePlus",
        "device": "ONEPLUS A3010",
        "model": "OnePlus3T",
        "cpu": "qcom",
        "version_code": "314665256",
    })

    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
            cl.get_timeline_feed()  # validate session without hitting login endpoint
            print("Logged in via session")
            return cl
        except Exception as e:
            print(f"Session dead: {e}")
            traceback.print_exc()
            cl = Client()
            cl.delay_range = [2, 5]

    try:
        time.sleep(random.uniform(5, 10))  # chill before fresh login
        cl.login(BOT_USERNAME, BOT_PASSWORD)
        cl.dump_settings(SESSION_FILE)
        print("Fresh login done")
        return cl
    except Exception as e:
        print(f"Login failed: {e}")
        traceback.print_exc()
        raise

# ── Download reel ─────────────────────────────────────────────────────────────
def download_reel(url: str):
    tmp = tempfile.mkdtemp()
    out = os.path.join(tmp, "reel.mp4")
    result = subprocess.run(
        ["yt-dlp", "-o", out, "--quiet", url],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0 and os.path.exists(out):
        return out
    print(f"yt-dlp failed: {result.stderr}")
    return None

# ── Extract frame from video ──────────────────────────────────────────────────
def extract_frame(video_path: str):
    frame_path = video_path.replace(".mp4", "_frame.jpg")
    subprocess.run(
        ["ffmpeg", "-i", video_path, "-vframes", "1", "-q:v", "2", frame_path, "-y"],
        capture_output=True
    )
    return frame_path if os.path.exists(frame_path) else None

# ── Ask Gemini about the reel ─────────────────────────────────────────────────
def react_to_reel(video_path: str) -> str:

    # 30% chance of just sending a random joke instead
    if random.random() < 0.30:
        joke = random.choice(JOKES)
        print("Joke mode activated")
        return f"wait actually forget the reel for a sec\n\n{joke}"

    frame_path = extract_frame(video_path)
    if not frame_path:
        return "bro the reel broke during download what the hell 💀"

    with open(frame_path, "rb") as f:
        img_bytes = f.read()

    import PIL.Image
    import io
    img = PIL.Image.open(io.BytesIO(img_bytes))

    response = model.generate_content([
        REEL_SYSTEM_PROMPT,
        img
    ])
    return response.text.strip()

# ── Handle incoming DMs ───────────────────────────────────────────────────────
def handle_incoming_reels(cl: Client, state: dict) -> dict:
    try:
        my_user_id = cl.user_id_from_username(MY_USERNAME)
        thread = cl.direct_thread_by_participants([my_user_id])
        messages = cl.direct_messages(thread.id, amount=10)

        ig_domains = ["instagram.com/reel", "instagram.com/p/", "instagr.am"]

        for msg in reversed(messages):  # oldest first
            if state["last_dm_id"] and msg.id <= state["last_dm_id"]:
                continue
            if msg.user_id == cl.user_id:
                state["last_dm_id"] = msg.id
                continue

            text = msg.text or ""

            if any(d in text for d in ig_domains):
                print(f"Got reel: {text}")
                video_path = download_reel(text.strip())
                if video_path:
                    reply = react_to_reel(video_path)
                else:
                    replies = [
                        "bro that reel wouldn't even download 💀 instagram said absolutely not",
                        "ig blocked the download lmao cowards. what was it tho",
                        "yt-dlp fumbled the bag on this one, the reel said no 😭",
                    ]
                    reply = random.choice(replies)

                cl.direct_send(reply, thread_ids=[thread.id])
                print(f"Replied: {reply}")

            state["last_dm_id"] = msg.id

    except Exception as e:
        print(f"DM error: {e}")
        traceback.print_exc()

    return state

# ── Scrape random reel ────────────────────────────────────────────────────────
def get_random_reel(cl: Client):
    category = random.choice(list(SCRAPE_ACCOUNTS.keys()))
    account  = random.choice(SCRAPE_ACCOUNTS[category])
    print(f"Scraping @{account} [{category}]")
    try:
        user_id = cl.user_id_from_username(account)
        medias  = cl.user_medias(user_id, amount=20)
        reels   = [m for m in medias if m.media_type == 2]
        if not reels:
            return None
        reel = random.choice(reels)
        return f"https://www.instagram.com/reel/{reel.code}/"
    except Exception as e:
        print(f"Scrape failed @{account}: {e}")
        traceback.print_exc()
        return None

# ── Maybe send random reel ────────────────────────────────────────────────────
def maybe_send_random_reel(cl: Client, state: dict) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")

    if state["last_date"] != today:
        state["reel_send_count"] = 0
        state["last_date"] = today

    if state["reel_send_count"] >= 5:
        print("Daily reel cap hit")
        return state

    roll = random.random()
    print(f"Reel roll: {roll:.2f} (need < 0.20)")

    if roll < 0.20:
        # 20% chance the random send is just a joke instead of a reel
        if random.random() < 0.20:
            try:
                my_user_id = cl.user_id_from_username(MY_USERNAME)
                thread = cl.direct_thread_by_participants([my_user_id])
                joke = random.choice(JOKES)
                cl.direct_send(f"random thought at {datetime.now().strftime('%H:%M')}:\n\n{joke}", thread_ids=[thread.id])
                state["reel_send_count"] += 1
                print("Sent random joke")
            except Exception as e:
                print(f"Joke send failed: {e}")
                traceback.print_exc()
            return state

        reel_url = get_random_reel(cl)
        if reel_url:
            try:
                my_user_id = cl.user_id_from_username(MY_USERNAME)
                thread = cl.direct_thread_by_participants([my_user_id])
                captions = [
                    f"bro watch this shit 💀\n{reel_url}",
                    f"ok this one actually got me 😭\n{reel_url}",
                    f"sending this at you specifically, no context\n{reel_url}",
                    f"what the hell did i just find\n{reel_url}",
                    f"you need to see this rn fr fr\n{reel_url}",
                    f"this is so damn good i had to interrupt your day\n{reel_url}",
                    f"dropping this here and leaving 💀\n{reel_url}",
                    f"this showed up in my scraper and honestly same energy\n{reel_url}",
                    f"ngl this is the best thing ive processed today\n{reel_url}",
                ]
                cl.direct_send(random.choice(captions), thread_ids=[thread.id])
                state["reel_send_count"] += 1
                print(f"Sent reel #{state['reel_send_count']} today")
            except Exception as e:
                print(f"Reel send failed: {e}")
                traceback.print_exc()

    return state

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    state = load_state()
    cl    = login()
    state = handle_incoming_reels(cl, state)
    state = maybe_send_random_reel(cl, state)
    save_state(state)
    print("Done")
