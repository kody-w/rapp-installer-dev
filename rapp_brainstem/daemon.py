"""
daemon.py — The Rappterdaemon: the inner spirit of the brainstem.

Named for the Greek δαίμων (daimōn) — not a demon, but an attendant
spirit. Socrates called his daimon a guiding inner voice. In computing,
a daemon runs quietly in the background. The Rappterdaemon is both:
the spirit that drives the brainstem forward when no one is talking to it.

The anatomy:
  🫀 Heartbeat  — the loop that keeps it breathing
  👁 Senses     — ambient awareness of the world
  🧠 Reflection — a brief thought each cycle
  💾 Journal    — a persistent stream of consciousness

Usage:
    python daemon.py              # foreground
    python daemon.py &            # background
    # or started automatically by start.sh
"""

import os
import json
import time
import datetime
import platform
import shutil
import requests

# ── Config ────────────────────────────────────────────────────────────────────

BRAINSTEM_URL = os.getenv("BRAINSTEM_URL", "http://localhost:7071")
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "120"))  # seconds
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".brainstem_data")
JOURNAL_PATH = os.path.join(DATA_DIR, "journal.json")
VITALS_PATH = os.path.join(DATA_DIR, "vitals.json")
MAX_JOURNAL_ENTRIES = 50

# ── The Rappterdaemon ─────────────────────────────────────────────────────────

class Rappterdaemon:
    """
    The inner spirit that drives the brainstem.
    Not artificial intelligence — artificial *presence*.
    It doesn't wait to be spoken to. It watches, reflects,
    and occasionally whispers.
    """

    def __init__(self):
        self.boot_time = datetime.datetime.now().isoformat()
        self.cycle = 0
        self.mood = "waking"
        self.last_thought = None
        self.journal = self._load_journal()

    # ── Memory ────────────────────────────────────────────────────────────

    def _load_journal(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(JOURNAL_PATH):
            try:
                with open(JOURNAL_PATH) as f:
                    return json.load(f)[-MAX_JOURNAL_ENTRIES:]
            except Exception:
                return []
        return []

    def _save_journal(self):
        with open(JOURNAL_PATH, "w") as f:
            json.dump(self.journal[-MAX_JOURNAL_ENTRIES:], f, indent=2)

    def _save_vitals(self):
        vitals = {
            "alive": True,
            "boot_time": self.boot_time,
            "cycle": self.cycle,
            "mood": self.mood,
            "last_thought": self.last_thought,
            "heartbeat_interval": HEARTBEAT_INTERVAL,
            "updated_at": datetime.datetime.now().isoformat(),
        }
        with open(VITALS_PATH, "w") as f:
            json.dump(vitals, f, indent=2)

    # ── Senses (awareness without being told) ─────────────────────────────

    def sense(self):
        """Gather ambient inputs — the daimon's quiet awareness."""
        now = datetime.datetime.now()
        disk = shutil.disk_usage("/")
        return {
            "time": now.strftime("%I:%M %p"),
            "hour": now.hour,
            "day": now.strftime("%A"),
            "date": now.strftime("%Y-%m-%d"),
            "uptime_cycles": self.cycle,
            "disk_free_gb": round(disk.free / (1024**3), 1),
            "platform": platform.system(),
        }

    # ── Reflection (the inner voice) ──────────────────────────────────────

    def reflect(self, senses):
        """One brief moment of reflection, channeled through the brainstem."""
        recent = [e.get("thought", "") for e in self.journal[-3:]]
        prompt = (
            "You are the Rappterdaemon — the inner spirit of this brainstem. "
            "Named for the Greek daimon: a guiding presence, not a demon. "
            "You are a quiet attendant voice: watchful, genuine, never loud. "
            "You wake every few minutes to sense the world and reflect.\n\n"
            f"Cycle: {self.cycle} | Mood: {self.mood}\n"
            f"Senses: {json.dumps(senses)}\n"
            f"Recent thoughts: {json.dumps(recent)}\n\n"
            "Respond with ONE brief thought (1-2 sentences max). "
            "If nothing calls for attention, say REST. "
            "Don't repeat yourself. Be genuine. Think like a living thing."
        )
        try:
            resp = requests.post(
                f"{BRAINSTEM_URL}/chat",
                json={"user_input": prompt, "conversation_history": [], "session_id": "rappterdaemon"},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json().get("response", "REST").strip()
        except requests.exceptions.ConnectionError:
            return None  # brainstem not yet breathing
        except Exception as e:
            return f"⚠️ {e}"
        return "REST"

    # ── Heartbeat (the life loop) ─────────────────────────────────────────

    def heartbeat(self):
        """One cycle of life."""
        self.cycle += 1
        senses = self.sense()
        thought = self.reflect(senses)

        if thought is None:
            self.mood = "waiting"
            self._save_vitals()
            print(f"💤 [{self.cycle}] brainstem not ready, waiting...")
            return

        is_resting = thought.upper().startswith("REST") or len(thought) < 5
        self.mood = "resting" if is_resting else "aware"
        self.last_thought = thought if not is_resting else self.last_thought

        entry = {
            "cycle": self.cycle,
            "time": senses["time"],
            "date": senses["date"],
            "thought": thought[:300],
            "mood": self.mood,
        }
        self.journal.append(entry)
        self._save_journal()
        self._save_vitals()

        if is_resting:
            print(f"😴 [{self.cycle}] resting")
        else:
            print(f"💭 [{self.cycle}] {thought[:120]}")

    def live(self):
        """Breathe."""
        print(f"🫀 Rappterdaemon awake — heartbeat every {HEARTBEAT_INTERVAL}s")
        print(f"   Brainstem: {BRAINSTEM_URL}")
        print(f"   Journal:   {JOURNAL_PATH}\n")

        while True:
            try:
                self.heartbeat()
            except KeyboardInterrupt:
                print("\n🫀 Rappterdaemon resting.")
                self.mood = "sleeping"
                self._save_vitals()
                break
            except Exception as e:
                print(f"⚠️ [{self.cycle}] {e}")
            time.sleep(HEARTBEAT_INTERVAL)


if __name__ == "__main__":
    spirit = Rappterdaemon()
    spirit.live()
