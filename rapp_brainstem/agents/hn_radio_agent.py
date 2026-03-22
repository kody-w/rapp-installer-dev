"""
Hacker News Radio Show — RAPP Single File Agent
------------------------------------------------
Scrapes HN, summarizes with the brainstem's AI, generates audio.
No API keys. No external servers. Just OpenRappter + macOS.

Drop into: ~/.brainstem/src/rapp_brainstem/agents/
Tell your Rappter: "make me a hacker news radio show"
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from openrappter.agents.basic_agent import BasicAgent
    HAS_BASIC = True
except ImportError:
    HAS_BASIC = False

# ── Agent Metadata (RAPP pattern) ──
AGENT = {
    "name": "HNRadio",
    "description": "Generate a Hacker News radio show. Scrapes top stories, summarizes with AI, creates audio. Say 'make me a hacker news radio show' or 'hn radio 5' for 5 articles.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Request like 'make a radio show' or 'hn radio 3 articles'"
            },
            "articles": {
                "type": "integer",
                "description": "Number of articles (default 5)"
            },
            "voice": {
                "type": "string",
                "description": "macOS voice name (default Daniel)"
            }
        },
        "required": []
    }
}

# ── Constants ──
HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"
OUTPUT_DIR = Path.home() / "Desktop"


def run(**kwargs) -> str:
    """Generate a Hacker News radio show."""
    query = kwargs.get("query", "")
    num_articles = kwargs.get("articles", 5)
    voice = kwargs.get("voice", "Daniel")

    # Parse article count from query
    nums = re.findall(r'\d+', query)
    if nums:
        num_articles = min(int(nums[0]), 10)

    try:
        # 1. Fetch top stories
        stories = fetch_top_stories(num_articles)
        if not stories:
            return json.dumps({"status": "error", "message": "Could not fetch HN stories"})

        # 2. Generate script using the brainstem's own AI
        script = generate_script(stories)

        # 3. Generate audio
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_file = OUTPUT_DIR / f"hn_radio_{timestamp}.m4a"
        script_file = OUTPUT_DIR / f"hn_radio_{timestamp}.txt"

        # Save script
        script_file.write_text(script)

        # Generate audio with macOS say
        generate_audio(script, str(audio_file), voice)

        # 4. Play it
        subprocess.Popen(["afplay", str(audio_file)])

        return json.dumps({
            "status": "success",
            "message": f"HN Radio generated! {num_articles} stories. Playing now.",
            "audio": str(audio_file),
            "script": str(script_file),
            "stories": [s["title"] for s in stories],
            "duration_estimate": f"~{len(script.split()) // 150} minutes"
        })

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def fetch_top_stories(count: int = 5) -> list:
    """Fetch top HN stories using stdlib only."""
    import urllib.request

    try:
        # Get top story IDs
        with urllib.request.urlopen(HN_TOP, timeout=10) as r:
            ids = json.loads(r.read())[:count]

        stories = []
        for sid in ids:
            try:
                with urllib.request.urlopen(HN_ITEM.format(sid), timeout=10) as r:
                    item = json.loads(r.read())
                    if item:
                        # Fetch top 3 comments
                        comments = []
                        for cid in (item.get("kids", []))[:3]:
                            try:
                                with urllib.request.urlopen(HN_ITEM.format(cid), timeout=5) as cr:
                                    comment = json.loads(cr.read())
                                    if comment and comment.get("text"):
                                        # Strip HTML from comment
                                        text = re.sub(r'<[^>]+>', '', comment["text"])
                                        comments.append({
                                            "author": comment.get("by", "anon"),
                                            "text": text[:300]
                                        })
                            except Exception:
                                pass

                        stories.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                            "score": item.get("score", 0),
                            "by": item.get("by", ""),
                            "comments_count": item.get("descendants", 0),
                            "comments": comments
                        })
            except Exception:
                pass
            time.sleep(0.1)

        return stories
    except Exception as e:
        print(f"Error fetching HN: {e}")
        return []


def generate_script(stories: list) -> str:
    """Generate radio script using the brainstem's copilot CLI."""
    today = datetime.now().strftime("%A, %B %d, %Y")

    prompt = f"""Write a radio show script for "Hacker News Radio" for {today}.

Be enthusiastic, conversational, natural. This will be read aloud.
Include: intro, each story summary with commentary, transitions, conclusion.
Do NOT use markdown, bullet points, or any formatting — pure spoken word.
Keep it under 2000 words total.

Today's top stories:
"""
    for i, s in enumerate(stories, 1):
        prompt += f"\n{i}. {s['title']} (Score: {s['score']}, {s['comments_count']} comments, by {s['by']})\n"
        prompt += f"   URL: {s['url']}\n"
        if s['comments']:
            prompt += "   Top comments:\n"
            for c in s['comments']:
                prompt += f"   - {c['author']}: {c['text'][:200]}\n"

    # Try copilot CLI first (OpenRappter's brain)
    try:
        result = subprocess.run(
            ["copilot", "--message", prompt],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            script = result.stdout.strip()
            # Clean any markdown
            script = re.sub(r'```[^`]*```', '', script)
            script = re.sub(r'[#*_`]', '', script)
            return clean_for_speech(script)
    except Exception:
        pass

    # Fallback: try Ollama
    try:
        import urllib.request
        payload = json.dumps({
            "model": "llama3.2",
            "prompt": prompt,
            "stream": False
        }).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            result = json.loads(r.read())
            if result.get("response"):
                return clean_for_speech(result["response"])
    except Exception:
        pass

    # Final fallback: basic script from data
    script = f"Welcome to Hacker News Radio for {today}! Here are today's top stories.\n\n"
    for i, s in enumerate(stories, 1):
        script += f"Story number {i}: {s['title']}. "
        script += f"This story has {s['score']} points and {s['comments_count']} comments. "
        if s['comments']:
            script += f"Top commenter {s['comments'][0]['author']} says: {s['comments'][0]['text'][:100]}. "
        script += "\n\n"
    script += "That's all for today's Hacker News Radio. Stay curious, stay building. See you next time!"
    return script


def clean_for_speech(text: str) -> str:
    """Clean text for TTS."""
    text = re.sub(r'https?://\S+', 'link', text)
    text = re.sub(r'[#*_`\[\]()]', '', text)
    text = text.replace('&', 'and')
    text = text.replace('<', 'less than')
    text = text.replace('>', 'greater than')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def generate_audio(script: str, output_path: str, voice: str = "Daniel"):
    """Generate audio using macOS say command."""
    # Write script to temp file
    tmp = Path(output_path).with_suffix(".txt")
    tmp.write_text(script)

    # Generate AIFF
    aiff = Path(output_path).with_suffix(".aiff")
    subprocess.run(
        ["say", "-v", voice, "-r", "175", "-f", str(tmp), "-o", str(aiff)],
        capture_output=True, timeout=300
    )

    # Convert to m4a
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(aiff), "-c:a", "aac", "-b:a", "128k", str(output_path)],
        capture_output=True, timeout=120
    )

    # Cleanup
    aiff.unlink(missing_ok=True)


# ── BasicAgent wrapper (optional, for OpenRappter compatibility) ──
if HAS_BASIC:
    class HNRadioAgent(BasicAgent):
        def __init__(self):
            self.name = "HNRadio"
            self.metadata = AGENT
            super().__init__(name=self.name, metadata=self.metadata)

        def perform(self, **kwargs):
            return run(**kwargs)
