"""English phrases -> Kazakh subtitles with the Claude API (optional step).

Needs ANTHROPIC_API_KEY (or an `ant auth login` profile). Without it, write
subtitles.json by hand: the format is the same list this function returns.
"""
import json

MODEL = "claude-opus-5-5"

SYSTEM = (
    "You translate English interview speech into Kazakh video subtitles. "
    "Translate meaning faithfully: do not shorten, add or soften information, keep names, brands and numbers. "
    "Use correct modern Kazakh spelling (Cyrillic, with ә ғ қ ң ө ұ ү һ і). "
    "Each item is one on-screen subtitle; keep each translation natural on its own and in order. "
    "Wrap the 1-3 most important words of an item (brand, numbers, key claim) in *asterisks* for highlighting; "
    "many items need none. If an item is already Kazakh or Russian speech, return it as correct Kazakh text."
)


def translate(phrases, context=""):
    import anthropic

    client = anthropic.Anthropic()
    items = [{"id": i, "en": p["en"]} for i, p in enumerate(phrases)]
    schema = {
        "type": "object",
        "properties": {"items": {"type": "array", "items": {
            "type": "object",
            "properties": {"id": {"type": "integer"}, "kk": {"type": "string"}},
            "required": ["id", "kk"], "additionalProperties": False}}},
        "required": ["items"], "additionalProperties": False,
    }
    user = (f"Context: {context}\n\n" if context else "") + \
        "Translate each item into Kazakh:\n" + json.dumps(items, ensure_ascii=False, indent=1)
    try:
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM,
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": schema}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.AuthenticationError:
        raise SystemExit("Claude API: no valid credentials. Set ANTHROPIC_API_KEY, or write subtitles.json by hand.")
    except anthropic.RateLimitError:
        raise SystemExit("Claude API: rate limited, try again in a minute.")
    except anthropic.APIConnectionError:
        raise SystemExit("Claude API: network error.")
    if resp.stop_reason == "refusal":
        raise SystemExit("Claude API declined the request; translate subtitles.json by hand.")
    if resp.stop_reason == "max_tokens":
        raise SystemExit("Claude API: output was cut off; translate in smaller parts.")
    text = next(b.text for b in resp.content if b.type == "text")
    kk = {it["id"]: it["kk"] for it in json.loads(text)["items"]}
    return [{"start": p["start"], "end": p["end"], "en": p["en"], "kk": kk.get(i, "")}
            for i, p in enumerate(phrases)]
