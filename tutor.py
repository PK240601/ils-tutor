"""LLM calls: generate questions, mark answers, write mini-lessons (OpenAI Responses API)."""
import json
from openai import OpenAI

MODEL = "gpt-5.4-mini"

SYSTEM = (
    "You are an expert UK Resuscitation Council (RCUK) Immediate Life Support (ILS) instructor "
    "tutoring a registered nurse. Base every question, answer and lesson ONLY on the reference "
    "facts provided. Never invent doses, timings or numbers that are not in the facts. "
    "Use UK spelling and UK clinical terms. Be encouraging and concise."
)

QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "options": {"type": "array", "items": {"type": "string"},
                    "description": "4 options for multiple_choice, empty list otherwise"},
        "correct_option_index": {"type": "integer", "description": "0-3 for multiple_choice, -1 otherwise"},
        "model_answer": {"type": "string"},
        "fact_used": {"type": "string"},
    },
    "required": ["question", "options", "correct_option_index", "model_answer", "fact_used"],
    "additionalProperties": False,
}

MARK_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["correct", "partial", "incorrect"]},
        "feedback": {"type": "string", "description": "1-2 sentences on what they got right or missed"},
    },
    "required": ["verdict", "feedback"],
    "additionalProperties": False,
}

LESSON_SCHEMA = {
    "type": "object",
    "properties": {
        "lesson": {"type": "string", "description": "Short markdown lesson, max ~150 words"},
        "memory_tip": {"type": "string"},
    },
    "required": ["lesson", "memory_tip"],
    "additionalProperties": False,
}


class Tutor:
    def __init__(self, api_key, model=MODEL):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _ask(self, prompt, schema, name):
        resp = self.client.responses.create(
            model=self.model,
            instructions=SYSTEM,
            input=prompt,
            text={"format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}},
        )
        return json.loads(resp.output_text)

    @staticmethod
    def _facts(topic):
        return "\n".join(f"- {f}" for f in topic["key_facts"])

    def make_question(self, topic, style, recent_questions=()):
        styles = {
            "multiple_choice": "a multiple-choice question with exactly 4 options and one correct answer",
            "short_answer": "a short-answer recall question answerable in one or two sentences",
            "scenario": "a brief realistic ward scenario (2-3 sentences) ending in a question about what to do or why",
        }
        avoid = "\n".join(f"- {q}" for q in recent_questions[-8:]) or "none"
        prompt = (
            f"Topic: {topic['name']}\nReference facts:\n{self._facts(topic)}\n"
            f"Common mistakes learners make:\n" + "\n".join(f"- {m}" for m in topic["common_mistakes"]) +
            f"\n\nWrite {styles[style]}. Test one fact. Where natural, make a wrong option match a common mistake.\n"
            f"Do not repeat these recent questions:\n{avoid}"
        )
        q = self._ask(prompt, QUESTION_SCHEMA, "ils_question")
        q["style"] = style
        if style != "multiple_choice":
            q["options"], q["correct_option_index"] = [], -1
        return q

    def mark(self, topic, question, answer):
        prompt = (
            f"Reference facts:\n{self._facts(topic)}\n\nQuestion: {question['question']}\n"
            f"Model answer: {question['model_answer']}\nLearner's answer: {answer}\n\n"
            "Mark it. 'correct' if the key clinical point is right (wording can differ), "
            "'partial' if incomplete but not unsafe, 'incorrect' if wrong or unsafe."
        )
        return self._ask(prompt, MARK_SCHEMA, "ils_mark")

    def lesson(self, topic, question=None, answer=None):
        context = ""
        if question:
            context = (f"\nThe learner was asked: {question['question']}\n"
                       f"They answered: {answer}\nCorrect answer: {question['model_answer']}\n"
                       "Start by addressing their specific misunderstanding.")
        prompt = (f"Topic: {topic['name']}\nReference facts:\n{self._facts(topic)}\n{context}\n"
                  "Teach a short, clear mini-lesson on this, with bullet points.")
        return self._ask(prompt, LESSON_SCHEMA, "ils_lesson")
