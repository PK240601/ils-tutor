"""Save each learner's progress. Uses Supabase when configured, else a local JSON file (for testing)."""
import hashlib
import json
import os
from datetime import datetime, timezone


def hash_pin(username, pin):
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), f"ils-tutor:{username}".encode(), 200_000).hex()


def normalise(username):
    return username.strip().lower()


class LocalStore:
    def __init__(self, path="local_progress.json"):
        self.path = path
        self.data = json.load(open(path)) if os.path.exists(path) else {}

    def get(self, username):
        return self.data.get(username)

    def save(self, username, pin_hash, state):
        self.data[username] = {"pin_hash": pin_hash, "state": state}
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=1)


class SupabaseStore:
    def __init__(self, url, key):
        from supabase import create_client
        self.db = create_client(url, key)

    def get(self, username):
        rows = self.db.table("learners").select("pin_hash,state").eq("username", username).execute().data
        return rows[0] if rows else None

    def save(self, username, pin_hash, state):
        self.db.table("learners").upsert({
            "username": username, "pin_hash": pin_hash, "state": state,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()


def login(store, username, pin):
    """Returns (state, error). Creates a new learner if the name is unused."""
    username = normalise(username)
    if not username or len(pin) < 4:
        return None, "Enter a name and a PIN of at least 4 digits."
    pin_hash = hash_pin(username, pin)
    row = store.get(username)
    if row is None:
        store.save(username, pin_hash, {})
        return {}, None
    if row["pin_hash"] != pin_hash:
        return None, "That name is taken, or the PIN is wrong."
    return row["state"] or {}, None
