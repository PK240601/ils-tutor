# ILS Tutor

An adaptive quiz coach for adult **Immediate Life Support (ILS)** theory, based on the Resuscitation Council UK (RCUK) 2025 guidelines. Built with Streamlit and the OpenAI Responses API (default model `gpt-5.4-mini`).

The tutor works out what you don't know yet, teaches it in short lessons, and keeps quizzing you until you have mastered all 15 topics.

> **Study aid only.** Always follow your local policy and the current RCUK ILS manual.

## Features

- **15 topics in 5 domains:** recognising deterioration, preventing cardiac arrest, CPR/defibrillation/airway, the ALS algorithm and drugs, and team skills/post-arrest care/decisions.
- **Adaptive questions:** it always picks your weakest due topic and avoids asking the same topic twice in a row.
- **Questions get harder as you improve:** multiple choice while you are weak, then short free-text answers, then ward scenarios.
- **Mini-lessons:** after any wrong or partial answer you get a short lesson with a memory tip. You can also ask for a lesson on any topic from the sidebar.
- **Spaced repetition:** topics you know well come back less often.
- **Grounded answers:** the model may only use the reference facts in `data/ils_topics.json`, so it should not invent doses or timings.
- **Simple login:** name and PIN. Progress is saved to Supabase, or to a local file while testing.

## How mastery works

Each topic is scored 0 to 5:

| Score | Level | Question style | Due again in |
|---|---|---|---|
| 0 | Not seen | Multiple choice | Now |
| 1 | Weak | Multiple choice | Now |
| 2 | Learning | Multiple choice or short answer | 1 day |
| 3 | Good | Short answer or scenario | 2 days |
| 4 | Strong | Short answer or scenario | 4 days |
| 5 | Mastered | Short answer or scenario | 7 days |

- **Correct:** +1. A topic reaches 5 only after correct answers on **3 different days**.
- **Partial:** no change (minimum score 1).
- **Incorrect:** −2 (minimum 1), and the count of correct days resets to the most recent one.

When nothing is due, the tutor keeps practising your weakest topics. You become an "expert" once every topic is at 5.

The rules live in `mastery.py` (`INTERVAL_DAYS`, `DAYS_NEEDED_FOR_MASTERY`).

## Project layout

| File | What it does |
|---|---|
| `app.py` | Streamlit interface: login, quiz, feedback, sidebar progress |
| `tutor.py` | OpenAI calls: write a question, mark a free-text answer, write a lesson (structured JSON outputs) |
| `mastery.py` | Scoring, spaced repetition, picking the next topic and question style. Plain Python with no API calls |
| `storage.py` | Name + PIN login (PIN hashed with PBKDF2) and saving progress to Supabase or `local_progress.json` |
| `data/ils_topics.json` | Topics, learning objectives, reference facts and common mistakes |
| `schema.sql` | Supabase table for learner progress |
| `.streamlit/secrets.toml` | Your API keys (git-ignored) |

## Run it locally

You need Python 3.10+ and an OpenAI API key.

```bash
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` from the example file (`.streamlit/secrets.toml.example`):

```toml
OPENAI_API_KEY = "sk-..."
# OPENAI_MODEL = "gpt-5.4-mini"   # optional, change the model

# Delete these two lines to save progress to local_progress.json instead
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_KEY = "your-service-role-key"
```

Then start the app:

```bash
streamlit run app.py
```

It opens at http://localhost:8501. Enter a name and choose a PIN of at least 4 digits. A new name creates a new learner.

## Deploy it for free

1. **Supabase:** create a free project at [supabase.com](https://supabase.com). In the SQL Editor, run `schema.sql`. Copy the Project URL and the `service_role` key from **Project Settings > API**.
   The app connects with the service role key from the server, so row level security stays on with no public policies. Never put this key in client-side code.
2. **GitHub:** push this folder to a new repository. `secrets.toml`, `local_progress.json` and `.venv/` are git-ignored.
3. **Streamlit Community Cloud:** at [share.streamlit.io](https://share.streamlit.io), choose **New app**, pick the repository and set the main file to `app.py`. Under **Advanced settings > Secrets**, paste:
   ```toml
   OPENAI_API_KEY = "sk-..."
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_KEY = "service-role-key"
   ```
4. Share the `*.streamlit.app` link. It works on phones and laptops.

## Editing the content

Every question, marking decision and lesson is generated from `data/ils_topics.json`. Each topic has:

- `id`, `domain`, `name`
- `objectives`: what the learner should be able to do
- `key_facts`: the only facts the model is allowed to use
- `common_mistakes`: these help it write good distractors and lessons

Fix a fact there and the questions are fixed too. Add a new topic and existing learners pick it up automatically at score 0.

**Before sharing widely,** have a nurse or ILS instructor check `data/ils_topics.json` against the current RCUK ILS manual.

## Notes and limits

- Multiple-choice answers are marked in code. Free-text and scenario answers are marked by the model, which can occasionally be too strict or too lenient.
- Each question uses one API call, and each free-text answer and lesson uses another. Costs are small with `gpt-5.4-mini`, but keep an eye on your OpenAI usage.
- The PIN is a light barrier to stop learners overwriting each other's progress. It is not strong authentication.
- Each learner's history keeps their last 200 answers.
