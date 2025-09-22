from __future__ import annotations
import json, csv, re
from pathlib import Path
from typing import Dict, Any, List

import yaml  # pip install pyyaml
from prompt_lab.genai_client import GeminiClient
from google.genai import types

# --- Paths / setup ---
ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ROOT / "prompts" / "variants.yaml"
CASES = ROOT / "data" / "cases.json"
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)


# --- Helpers ---
def load_variants() -> Dict[str, Any]:
    # Use utf-8-sig to tolerate BOM on Windows
    return yaml.safe_load(VARIANTS.read_text(encoding="utf-8-sig"))


def render_prompt(variant: Dict[str, Any], case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns: {"prompt": str, "system": Optional[str], "mime": Optional[str]}
    Expands few_shots inline in a simple "User/Assistant" format for demo purposes.
    """
    sys = variant.get("system")
    tmpl = variant["prompt_template"]
    prompt = tmpl.format(task=case.get("task", ""), input=case.get("input", ""))

    # Inline few-shot examples if present
    shots = variant.get("few_shots", [])
    if shots:
        lines = []
        for s in shots:
            lines.append(f"User: {s['user']}\nAssistant: {s['model']}")
        fewshot_block = "\n\n".join(lines)
        prompt = (
            f"{fewshot_block}\n\n"
            f"User: {case.get('task','')}\n{case.get('input','')}\n"
            f"Assistant:"
        )

    return {"prompt": prompt, "system": sys, "mime": variant.get("response_mime_type")}


# --- Scoring ---
def score_summarize(output: str, case: Dict[str, Any]) -> Dict[str, Any]:
    words = len(output.split())
    max_words = int(case.get("max_words", 9999))
    # length score: 1.0 if within limit, linear penalty if over
    s_len = 1.0 if words <= max_words else max(0.0, 1 - (words - max_words) / max_words)

    kws = case.get("keywords") or []
    s_keys = 0.0
    if kws:
        hits = sum(1 for k in kws if re.search(re.escape(k), output, re.I))
        s_keys = hits / len(kws)

    return {
        "words": words,
        "score_len": round(s_len, 3),
        "score_keywords": round(s_keys, 3),
    }


def score_classify(output: str, case: Dict[str, Any]) -> Dict[str, Any]:
    # Prefer JSON; fallback to regex extraction of a label
    parsed = None
    try:
        parsed = json.loads(output)
    except Exception:
        m = re.search(r"(Positive|Neutral|Negative)", output, re.I)
        if m:
            parsed = {"label": m.group(1).capitalize(), "confidence": None}

    ok_json = 1.0 if isinstance(parsed, dict) and "label" in parsed else 0.0
    label = (parsed or {}).get("label")
    expect = case.get("expected_label")
    match = 1.0 if (label and expect and label.lower() == expect.lower()) else 0.0

    return {"ok_json": ok_json, "label": label, "score_label": match}


# --- Main ---
def main():
    cfg = load_variants()
    defaults = cfg.get("defaults", {})
    variants = cfg.get("variants", [])

    # Read JSON with utf-8-sig to strip BOM if present
    cases_text = CASES.read_text(encoding="utf-8-sig")
    cases = json.loads(cases_text)

    client = GeminiClient(model=defaults.get("model", None))

    rows: List[Dict[str, Any]] = []
    for v in variants:
        vid = v["id"]
        allowed = set(v.get("applies_to", ["summarize", "classify"]))
        for case in cases:
            if case["type"] not in allowed:
                continue
            rendered = render_prompt(v, case)

            temp = float(defaults.get("temperature", 0.7))
            max_tok = int(defaults.get("max_output_tokens", 256))

            # If variant requests JSON-only, set response_mime_type
            if rendered["mime"]:
                resp = client.client.models.generate_content(
                    model=client.model,
                    contents=rendered["prompt"],
                    config=types.GenerateContentConfig(
                        response_mime_type=rendered["mime"],
                        system_instruction=v.get("system"),
                        temperature=temp,
                        max_output_tokens=max_tok,
                    ),
                )
                text = resp.text
            else:
                resp = client.generate_text(
                    rendered["prompt"],
                    system_instruction=v.get("system"),
                    temperature=temp,
                    max_output_tokens=max_tok,
                )
                text = resp.text

            result: Dict[str, Any] = {
                "variant": vid,
                "case_id": case["id"],
                "type": case["type"],
                "output": (text or "").strip(),
            }

            if case["type"] == "summarize":
                result.update(score_summarize(text, case))
                result["total_score"] = round(
                    (result["score_len"] + result["score_keywords"]) / 2, 3
                )
            elif case["type"] == "classify":
                result.update(score_classify(text, case))
                result["total_score"] = round(
                    (result["ok_json"] + result["score_label"]) / 2, 3
                )

            rows.append(result)
            print(f"[{vid} -> {case['id']}] total={result.get('total_score')}")

    # --- CSV (handle heterogeneous rows by using union of keys) ---
    out_csv = ARTIFACTS / "results.csv"
    core = ["variant", "case_id", "type", "output", "total_score"]
    metrics = sorted({k for r in rows for k in r.keys()} - set(core))
    fieldnames = core + metrics

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            for k in fieldnames:
                r.setdefault(k, "")
            w.writerow(r)

    # --- JSON ---
    out_json = ARTIFACTS / "results.json"
    out_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    print(f"\nWrote {out_csv} and {out_json}")


if __name__ == "__main__":
    main()
