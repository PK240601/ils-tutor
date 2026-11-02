"""Mastery tracking and spaced repetition. Pure Python, no API calls."""
import random
from datetime import date, timedelta

# Days to wait before a topic is due again, by score (0-5).
INTERVAL_DAYS = {0: 0, 1: 0, 2: 1, 3: 2, 4: 4, 5: 7}
DAYS_NEEDED_FOR_MASTERY = 3


def new_topic_state():
    return {"score": 0, "attempts": 0, "correct": 0, "correct_days": [], "due": None, "last_seen": None}


def ensure_topics(state, topics):
    """Add any topics missing from a learner's state (e.g. new topics added later)."""
    state.setdefault("topics", {})
    for t in topics:
        state["topics"].setdefault(t["id"], new_topic_state())
    state.setdefault("history", [])
    return state


def update(topic_state, verdict, today=None):
    """verdict: 'correct', 'partial' or 'incorrect'. Returns the updated state."""
    today = today or date.today()
    ts = topic_state
    ts["attempts"] += 1
    ts["last_seen"] = today.isoformat()

    if verdict == "correct":
        ts["correct"] += 1
        if today.isoformat() not in ts["correct_days"]:
            ts["correct_days"].append(today.isoformat())
        new_score = ts["score"] + 1
        # 5 is reserved for correct answers on several different days.
        if new_score >= 5 and len(ts["correct_days"]) < DAYS_NEEDED_FOR_MASTERY:
            new_score = 4
        ts["score"] = min(new_score, 5)
    elif verdict == "partial":
        ts["score"] = max(ts["score"], 1)  # no gain, small floor
    else:
        ts["score"] = max(1, ts["score"] - 2)
        ts["correct_days"] = ts["correct_days"][-1:]  # must re-earn spaced recall

    ts["due"] = (today + timedelta(days=INTERVAL_DAYS[ts["score"]])).isoformat()
    return ts


def pick_next_topic(state, topics, last_topic_id=None, today=None):
    """Pick the weakest due topic, avoiding an immediate repeat when possible."""
    today = (today or date.today()).isoformat()
    ids = [t["id"] for t in topics]
    due = [i for i in ids if (state["topics"][i]["due"] or today) <= today]
    pool = due or ids  # if nothing is due, keep practising the weakest
    if len(pool) > 1 and last_topic_id in pool:
        pool = [i for i in pool if i != last_topic_id]
    lowest = min(state["topics"][i]["score"] for i in pool)
    return random.choice([i for i in pool if state["topics"][i]["score"] == lowest])


def question_style(score):
    """Easier recall questions while weak, clinical scenarios once stronger."""
    if score <= 1:
        return "multiple_choice"
    if score == 2:
        return random.choice(["multiple_choice", "short_answer"])
    return random.choice(["short_answer", "scenario"])


def overall_progress(state):
    scores = [t["score"] for t in state["topics"].values()]
    return sum(scores) / (5 * len(scores)) if scores else 0.0


def is_expert(state):
    return all(t["score"] == 5 for t in state["topics"].values())
