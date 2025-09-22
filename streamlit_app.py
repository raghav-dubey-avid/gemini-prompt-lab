from __future__ import annotations
import json
from io import StringIO
from pathlib import Path
from typing import Dict, Any, List, Optional

import streamlit as st
import yaml
import os
from prompt_lab.genai_client import GeminiClient
from google.genai import types  # for JSON-only responses

from dotenv import load_dotenv
from pathlib import Path

# load .env from the project root no matter the working dir
load_dotenv(dotenv_path=Path(__file__).with_name(".env"), override=True)


# ------------------------------------------------------------------------------
# Page setup
# ------------------------------------------------------------------------------
st.set_page_config(page_title="Gemini Prompt Lab — Variant Explorer", page_icon="🤖", layout="wide")

# Read query param so the overlay can be closed with a link
if st.query_params.get("welcome") == "0":
    st.session_state.show_welcome = False


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
CSS_FILE = ASSETS / "styles.css"
VARIANTS = ROOT / "prompts" / "variants.yaml"
CASES = ROOT / "data" / "cases.json"

# Load CSS from file
if CSS_FILE.exists():
    st.markdown(f"<style>{CSS_FILE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
else:
    st.warning("Missing CSS at assets/styles.css — using default Streamlit styles.", icon="⚠️")

# ------------------------------------------------------------------------------
# Data loaders
# ------------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_variants() -> Dict[str, Any]:
    return yaml.safe_load(VARIANTS.read_text(encoding="utf-8-sig"))

@st.cache_data(show_spinner=False)
def load_cases() -> List[Dict[str, Any]]:
    return json.loads(CASES.read_text(encoding="utf-8-sig"))

def render_prompt(variant: Dict[str, Any], case: Dict[str, Any]) -> Dict[str, Optional[str]]:
    sys = variant.get("system")
    tmpl = variant["prompt_template"]
    prompt = tmpl.format(task=case.get("task",""), input=case.get("input",""))

    shots = variant.get("few_shots", [])
    if shots:
        lines = []
        for s in shots:
            lines.append(f"User: {s['user']}\nAssistant: {s['model']}")
        fewshot_block = "\n\n".join(lines)
        prompt = f"{fewshot_block}\n\nUser: {case.get('task','')}\n{case.get('input','')}\nAssistant:"
    return {"prompt": prompt, "system": sys, "mime": variant.get("response_mime_type")}

def call_model(variant: Dict[str, Any], case: Dict[str, Any], temp: float, max_tok: int, client: GeminiClient):
    rendered = render_prompt(variant, case)
    if rendered["mime"]:
        resp = client.client.models.generate_content(
            model=client.model,
            contents=rendered["prompt"],
            config=types.GenerateContentConfig(
                response_mime_type=rendered["mime"],
                system_instruction=variant.get("system"),
                temperature=temp,
                max_output_tokens=max_tok,
            ),
        )
        text = resp.text
    else:
        resp = client.generate_text(
            rendered["prompt"],
            system_instruction=variant.get("system"),
            temperature=temp,
            max_output_tokens=max_tok,
        )
        text = resp.text

    # token stats (prompt + output)
    try: t_prompt = client.count_tokens(rendered["prompt"])
    except Exception: t_prompt = None
    try: t_output = client.count_tokens(text or "")
    except Exception: t_output = None

    return {
        "variant": variant["id"],
        "title": variant.get("title", variant["id"]),
        "prompt": rendered["prompt"],
        "system": variant.get("system"),
        "output": text or "",
        "prompt_tokens": t_prompt,
        "output_tokens": t_output,
    }

def csv_from_rows(rows: List[Dict[str, Any]]) -> str:
    cols = ["variant", "title", "prompt_tokens", "output_tokens", "output"]
    s = StringIO(); s.write(",".join(cols) + "\n")
    for r in rows:
        vals = [
            r["variant"],
            r.get("title",""),
            str(r.get("prompt_tokens","") or ""),
            str(r.get("output_tokens","") or ""),
            json.dumps((r.get("output","") or "").replace("\n"," ").strip()),
        ]
        s.write(",".join(vals) + "\n")
    return s.getvalue()

# ------------------------------------------------------------------------------
# Welcome modal (one per session)
# ------------------------------------------------------------------------------
if "show_welcome" not in st.session_state:
    st.session_state.show_welcome = True

if st.session_state.show_welcome and st.query_params.get("welcome") != "0":
    st.markdown(
        """
<div class="modal-overlay">
  <div class="modal-card">
    <div class="mascot animate">
      <div class="face"></div>
      <div class="eye left"><div class="pupil"></div><div class="eyelid"></div></div>
      <div class="eye right"><div class="pupil"></div><div class="eyelid"></div></div>
      <div class="smile"></div>
    </div>
    <div class="modal-title">Hi! I’m <b>GENAI</b> 👋</div>
    <div class="modal-sub">Welcome to the world of AI — explore prompt variants, see the exact prompts, and measure results.</div>
    <!-- Same-tab close; no new window -->
    <a class="enter-btn" href="?welcome=0" aria-label="Enter the Lab">Let’s Go 🚀</a>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.stop()



# ------------------------------------------------------------------------------
# Main UI
# ------------------------------------------------------------------------------
st.markdown("<h1>🔭 <span class='gradient'>Gemini Prompt Lab — Variant Explorer</span></h1>", unsafe_allow_html=True)

cfg = load_variants()
defaults = cfg.get("defaults", {})
variants = cfg.get("variants", [])
cases = load_cases()

# Show a nice error if no key is visible
if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
    from dotenv import load_dotenv
    from pathlib import Path
    # try loading .env from root, then re-check
    load_dotenv(Path(__file__).with_name(".env"), override=False)

if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
    st.error(
        "API key not found. Create a `.env` at the repo root with:\n\n"
        "`GOOGLE_API_KEY=YOUR_REAL_KEY`\n\n"
        "Then restart the app.",
        icon="🔑",
    )
    st.stop()

client = GeminiClient(model=defaults.get("model", None))

left, right = st.columns([1, 1.6], gap="large")

with left:
    st.subheader("Variants")
    v_options = [v["id"] for v in variants]
    selected = st.multiselect(
        "Choose one or more variants to compare",
        v_options,
        default=[v_options[0]] if v_options else [],
    )

    st.subheader("Cases")
    case_id = st.selectbox("Choose a case", [c["id"] for c in cases], index=0)
    case = next(c for c in cases if c["id"] == case_id)

    def allowed(v, case):
        kinds = set(v.get("applies_to", ["summarize","classify"]))
        return case["type"] in kinds

    st.caption("Edit the input before running (optional):")
    input_text = st.text_area("Input text", value=case.get("input",""), height=140)
    case = {**case, "input": input_text}

    temp = st.slider("Temperature", 0.0, 1.0, float(defaults.get("temperature", 0.7)), 0.05)
    max_tok = st.slider("Max output tokens", 32, 2048, int(defaults.get("max_output_tokens", 256)), 32)

    run = st.button("Run 🔥", type="primary", use_container_width=True)

with right:
    st.subheader("Output")
    results: List[Dict[str, Any]] = []

    if run and selected:
        for vid in selected:
            v = next(v for v in variants if v["id"] == vid)
            if not allowed(v, case):
                st.info(f"Skipped **{vid}** (not applicable to `{case['type']}`)", icon="⏭️")
                continue
            with st.spinner(f"Running variant: {vid}"):
                res = call_model(v, case, temp, max_tok, client)
                results.append(res)

        # Display in a neat grid (2 columns)
        cols = st.columns(2, gap="large")
        for i, res in enumerate(results):
            with cols[i % 2]:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown(f"### ✨ {res['title']}  \n*Variant:* `{res['variant']}`")

                tabs = st.tabs(["Response", "Rendered prompt", "Metrics", "Download"])
                with tabs[0]:
                    st.write(res["output"])

                with tabs[1]:
                    st.code(res["prompt"], language="text")
                    if res.get("system"):
                        st.caption("System instruction:")
                        st.code(res["system"], language="markdown")

                with tabs[2]:
                    pt, ot = res.get("prompt_tokens"), res.get("output_tokens")
                    st.write(f"**Prompt tokens:** {pt if pt is not None else '—'}  |  **Output tokens:** {ot if ot is not None else '—'}")

                with tabs[3]:
                    st.download_button(
                        "Download response (.txt)",
                        data=(res["output"] or "").encode("utf-8"),
                        file_name=f"{res['variant']}_{case['id']}.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )

                st.markdown("</div>", unsafe_allow_html=True)

        if results:
            st.divider()
            st.markdown("#### Export all results")
            csv_data = csv_from_rows(results)
            json_data = json.dumps(results, indent=2).encode("utf-8")
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("Download CSV", data=csv_data.encode("utf-8"),
                                   file_name=f"results_{case['id']}.csv", mime="text/csv",
                                   use_container_width=True)
            with c2:
                st.download_button("Download JSON", data=json_data,
                                   file_name=f"results_{case['id']}.json", mime="application/json",
                                   use_container_width=True)
    else:
        st.info("Pick one or more **variants**, choose a **case**, then click **Run**.", icon="👉")
