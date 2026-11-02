"""ILS Tutor: an adaptive Immediate Life Support quiz coach. Run with: streamlit run app.py"""
import json
from datetime import date
from pathlib import Path

import streamlit as st

import mastery
from storage import LocalStore, SupabaseStore, hash_pin, login, normalise
from tutor import Tutor

st.set_page_config(page_title="ILS Tutor", page_icon="❤️", layout="centered")

DATA = json.loads((Path(__file__).parent / "data" / "ils_topics.json").read_text())
TOPICS = DATA["topics"]
BY_ID = {t["id"]: t for t in TOPICS}
LEVEL = ["Not seen", "Weak", "Learning", "Good", "Strong", "Mastered"]


@st.cache_resource
def get_store():
    if "SUPABASE_URL" in st.secrets:
        return SupabaseStore(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    return LocalStore()


@st.cache_resource
def get_tutor():
    return Tutor(st.secrets["OPENAI_API_KEY"], st.secrets.get("OPENAI_MODEL", "gpt-5.4-mini"))


ss = st.session_state
store = get_store()


def save():
    store.save(ss.user, ss.pin_hash, ss.state)


def new_question():
    state = ss.state
    topic_id = mastery.pick_next_topic(state, TOPICS, ss.get("last_topic"))
    style = mastery.question_style(state["topics"][topic_id]["score"])
    recent = [h["q"] for h in state["history"] if h["topic"] == topic_id]
    with st.spinner("Writing your next question..."):
        ss.question = get_tutor().make_question(BY_ID[topic_id], style, recent)
    ss.question["topic"] = topic_id
    ss.last_topic = topic_id
    ss.phase, ss.result, ss.lesson = "ask", None, None


def submit(answer):
    q, topic = ss.question, BY_ID[ss.question["topic"]]
    with st.spinner("Marking..."):
        if q["style"] == "multiple_choice":
            ok = q["options"].index(answer) == q["correct_option_index"]
            result = {"verdict": "correct" if ok else "incorrect",
                      "feedback": "Correct!" if ok else f"The answer is: {q['options'][q['correct_option_index']]}"}
        else:
            result = get_tutor().mark(topic, q, answer)
        if result["verdict"] != "correct":
            ss.lesson = get_tutor().lesson(topic, q, answer)
    mastery.update(ss.state["topics"][topic["id"]], result["verdict"])
    ss.state["history"] = (ss.state["history"] + [
        {"topic": topic["id"], "q": q["question"], "verdict": result["verdict"], "date": date.today().isoformat()}
    ])[-200:]
    save()
    ss.result, ss.phase = result, "feedback"


# ---------- Login ----------
if "user" not in ss:
    st.title("❤️ ILS Tutor")
    st.write("Your personal coach for **Immediate Life Support** theory (RCUK 2025 guidelines). "
             "It finds what you don't know yet, teaches it, and keeps quizzing until you've mastered every topic.")
    with st.form("login"):
        name = st.text_input("Your name")
        pin = st.text_input("PIN (4+ digits; new users choose one now)", type="password")
        if st.form_submit_button("Start", type="primary"):
            state, err = login(store, name, pin)
            if err:
                st.error(err)
            else:
                ss.user, ss.pin_hash = normalise(name), hash_pin(normalise(name), pin)
                ss.state = mastery.ensure_topics(state, TOPICS)
                ss.phase = None
                st.rerun()
    st.caption("Study aid only. Always follow your local policy and the current RCUK ILS manual.")
    st.stop()

# ---------- Sidebar: progress ----------
with st.sidebar:
    st.subheader(f"Hi {ss.user.title()} 👋")
    st.progress(mastery.overall_progress(ss.state), text=f"Overall: {mastery.overall_progress(ss.state):.0%}")
    for t in TOPICS:
        s = ss.state["topics"][t["id"]]["score"]
        st.progress(s / 5, text=f"{t['name']}: {LEVEL[s]}")
    st.divider()
    pick = st.selectbox("Teach me a topic", ["—"] + [t["name"] for t in TOPICS])
    if pick != "—" and st.button("Show lesson"):
        topic = next(t for t in TOPICS if t["name"] == pick)
        with st.spinner("Preparing lesson..."):
            ss.lesson = get_tutor().lesson(topic)
        ss.phase = "lesson"
    if st.button("Log out"):
        ss.clear()
        st.rerun()

# ---------- Main ----------
st.title("❤️ ILS Tutor")

if mastery.is_expert(ss.state):
    st.balloons()
    st.success("🎉 You've mastered every ILS topic across several days. You're ready! Keep practising to stay sharp.")

if ss.phase is None:
    new_question()

if ss.phase == "lesson":
    st.markdown(ss.lesson["lesson"])
    st.info(f"💡 {ss.lesson['memory_tip']}")
    if st.button("Back to quiz", type="primary"):
        new_question()
        st.rerun()
    st.stop()

q = ss.question
topic = BY_ID[q["topic"]]
st.caption(f"{topic['name']} · {LEVEL[ss.state['topics'][topic['id']]['score']]}")
st.markdown(f"#### {q['question']}")

if ss.phase == "ask":
    with st.form("answer"):
        if q["style"] == "multiple_choice":
            answer = st.radio("Choose one", q["options"], index=None)
        else:
            answer = st.text_area("Your answer")
        if st.form_submit_button("Submit", type="primary"):
            if not answer:
                st.warning("Give an answer first. It's fine to guess!")
            else:
                ss.given = answer
                submit(answer)
                st.rerun()
else:
    r = ss.result
    {"correct": st.success, "partial": st.warning, "incorrect": st.error}[r["verdict"]](
        f"**{r['verdict'].title()}.** {r['feedback']}")
    if q["style"] != "multiple_choice":
        st.markdown(f"**Model answer:** {q['model_answer']}")
    if ss.lesson:
        with st.expander("📘 Quick lesson", expanded=True):
            st.markdown(ss.lesson["lesson"])
            st.info(f"💡 {ss.lesson['memory_tip']}")
    if st.button("Next question ➜", type="primary"):
        new_question()
        st.rerun()
