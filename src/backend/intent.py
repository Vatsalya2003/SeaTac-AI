"""
Templates mode (QUERY_MODE=templates): decide which of the Port's 10 questions is being asked.

One AI call. The model gets the question and a short menu (templates.QUESTIONS) and must reply with JSON only:
    {"question": "Q1".."Q10" or "other", "date": "YYYY-MM-DD" or null}
The reply is parsed and every field is checked against the menu. The AI never writes SQL here.

If the AI can't be reached (no key, quota, "high demand" errors), a keyword match is tried instead, so the
tested answers still work. parse() returns None when nothing valid comes back; the caller then falls back to
stage 1 (views mode, AI-written SQL).
"""
import json
import re

import templates

PROMPT = """You route questions for an airport-operations chatbot (Seattle-Tacoma airport, one day of data: {day}).
Pick the ONE menu item the question asks for. If none fits exactly, answer "other".

MENU
{menu}
- other: anything else (a different grouping, filter or measure than the items above, or not about this data)

Question: "{question}"

Reply with JSON only, no markdown, in this form:
{{"question": "Q1", "date": null}}
"date" is a date the question explicitly asks about, as YYYY-MM-DD, otherwise null."""


def menu_text():
    return "\n".join(f"- {qid}: {q['title']}: {q['description']}" for qid, q in templates.QUESTIONS.items())


def build_prompt(question):
    return PROMPT.format(day=templates.DEFAULT_DAY, menu=menu_text(), question=question.strip())


def parse_reply(text):
    """Model reply -> {"question", "date"} or None if it isn't valid JSON for the menu."""
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    qid = str(data.get("question", "")).strip().upper()
    if qid not in templates.QUESTIONS:      # includes "OTHER"
        return None
    day = data.get("date")
    if day in (None, "", "null"):
        day = None
    elif not (isinstance(day, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", day)):
        return None
    if set(data) - {"question", "date"}:
        return None
    return {"question": qid, "date": day}


# ---- keyword fallback (used only when the AI call fails) --------------------------------------------------------
# Order matters: more specific questions first.
KEYWORD_RULES = [
    ("Q10", [r"\bpeak hours?\b", r"\bbusiest hours?\b", r"\bhours?\b.*\bmost\b.*\b(activity|flights|operations|traffic)\b",
             r"\bmost\b.*\b(activity|operations)\b.*\bhour", r"\bbusiest\b.*\bhour"]),
    ("Q3", [r"\bmovement area\b", r"\b(at the same time|simultaneous(ly)?|at once)\b"]),
    ("Q7", [r"\btaxiways?\b", r"\btaxiway (segment|section)s?\b", r"\b(segment|section)s?\b.*\bused\b"]),
    ("Q6", [r"\bweight class", r"\b(heavy|medium|light|super)\b.*\b(aircraft|taxi)", r"\btaxi\b.*\b(heavy|medium|light)\b"]),
    ("Q4", [r"\brunway occupancy\b", r"\b(stay|time|long)\b.*\bon the runway\b", r"\boccupy\b.*\brunway\b"]),
    ("Q9", [r"\brunways?\b.*\b(take-?offs?|landings?|used|activity|utili[sz]ation|busiest|most)\b",
            r"\b(take-?offs?|landings?)\b.*\b(each|per|by)\b.*\brunway\b"]),
    ("Q5", [r"\b(take-?off|wheels-?up|departure)s?\b.*\b(delay|late)\b", r"\b(delay|late)\b.*\b(take-?off|departures?)\b",
            r"\bscheduled take-?off\b"]),
    ("Q2", [r"\btaxi-?\s?out\b", r"\btaxi before take-?off\b", r"\bdepartures?\b.*\btaxi\b"]),
    ("Q1", [r"\btaxi-?\s?in\b.*\b(aircraft|plane) types?\b", r"\b(aircraft|plane) types?\b.*\b(taxi|gate|park)",
            r"\bby aircraft type\b"]),
    ("Q8", [r"\bwheels-?\s?down to (parking|the gate|in-?block)\b", r"\bpark\b.*\b(after|from)\b.*\b(touch|land|wheels)",
            r"\b(touch(ing)? down|landing)\b.*\bto\b.*\b(park|gate)\b", r"\btaxi-?\s?in\b"]),
]


def keyword_match(question):
    q = re.sub(r"\s+", " ", question.lower())
    for qid, patterns in KEYWORD_RULES:
        if any(re.search(p, q) for p in patterns):
            return qid
    return None


def parse(question, client, model=None):
    """-> {"question", "date", "source": "ai" | "keywords"} or None (fall back to stage 1).

    client: the existing LLM client from app_optimized.py (Claude or Gemini, same messages.create interface), or None.
    """
    if client is not None:
        try:
            reply = client.messages.create(model=model, max_tokens=100, temperature=0,
                                           messages=[{"role": "user", "content": build_prompt(question)}])
            picked = parse_reply(reply.content[0].text)
            if picked:
                print(f"🧭 Intent (AI): {picked}")
                return dict(picked, source="ai")
            print("🧭 Intent (AI): other / invalid reply -> stage 1")
            return None
        except Exception as e:  # quota, "high demand", network: use the keyword match instead
            print(f"⚠️  Intent AI call failed ({str(e)[:120]}); trying keyword match")
    qid = keyword_match(question)
    if qid:
        print(f"🧭 Intent (keywords): {qid}")
        return {"question": qid, "date": None, "source": "keywords"}
    return None
