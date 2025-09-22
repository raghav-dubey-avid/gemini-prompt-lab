
# Gemini Prompt Lab (Python)

A small, production-style **prompt‑engineering lab** for Google’s Gemini API.  
It lets you:

- Try **multiple prompt variants** (baseline, rubric, few‑shot, JSON‑only)
- Inspect the **exact prompt** sent to the model (UI)
- **Evaluate and score** outputs on test cases (CSV/JSON artifacts)
- Run from a clean **CLI** or a sleek **Streamlit UI** with a playful GENAI mascot ✨

---

## ✨ Features

- **Official SDK** — uses the maintained `google-genai` client
- **Variants** — baseline / rubric / few‑shot / JSON‑only classification
- **Scoring** — simple heuristics:
  - Summaries: word‑limit compliance + keyword presence
  - Classification: valid JSON + correct label
- **Artifacts** — writes `artifacts/results.csv` and `artifacts/results.json`
- **UI** — Streamlit app with a welcome modal, animated mascot, side‑by‑side variant compare, token counts, and one‑click downloads
- **CLI** — Typer‑based, fast and scriptable

---

## 🗂 Repo Structure

```
gemini-prompt-lab/
├─ src/prompt_lab/
│  ├─ genai_client.py        # Gemini wrapper (loads .env, token count, text gen)
│  ├─ cli.py                 # Typer CLI (run/tokens)
│  └─ __init__.py
├─ prompts/
│  └─ variants.yaml          # all prompt variants live here
├─ data/
│  └─ cases.json             # test cases (summarize/classify)
├─ eval/
│  └─ run_eval.py            # runs variants on cases, scores, writes artifacts
├─ artifacts/                # generated: results.csv / results.json
├─ assets/
│  └─ styles.css             # UI styling + mascot animations
├─ streamlit_app.py          # UI to inspect and run variants
├─ requirements.txt
├─ pyproject.toml            # package metadata; exposes CLI command `gpl`
├─ .env                      # your GOOGLE_API_KEY (never commit)
├─ .gitignore
└─ README.md
```

---

## ✅ Prerequisites

- Python **3.9+**
- A **Google AI Studio** API key (free tier works)

Create a `.env` file in the project root (same folder as `streamlit_app.py`):

```
GOOGLE_API_KEY=your_real_key_here
```

> `.env` is ignored by Git. Never commit secrets.

---

## 🚀 Quick Start

### 1) Create & activate a virtual env

**Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install deps and the package (editable)

```bash
pip install -r requirements.txt
pip install -e .
```

### 3) Sanity check (CLI)

```bash
python -m prompt_lab.cli run --prompt "Say hello in 5 words."
```

You should see a short response printed to the console.

---

## 🧰 CLI Usage

After `pip install -e .`, you can use either the module or the console script.

**Module form (always works)**
```bash
python -m prompt_lab.cli run --prompt "List three crisp tips for writing prompts."
python -m prompt_lab.cli run --prompt "Rewrite this to be concise: We will reschedule the launch..." --system ./prompts/system.md
python -m prompt_lab.cli tokens "Explain cosine similarity in one sentence."
```

**Console script (`gpl`)**  
*(If `gpl` isn’t found, ensure your venv is active and re‑run `pip install -e .`.)*
```bash
gpl run --prompt "List three crisp tips for writing prompts."
gpl run --prompt "Rewrite this to be concise: We will reschedule the launch..." --system ./prompts/system.md --show-tokens
gpl tokens "Explain cosine similarity in one sentence."
```

**Useful flags**
- `--prompt` : text **OR** path to a `.txt` file
- `--system` : optional system prompt file (Markdown)
- `--model` : override model (default is `gemini-1.5-flash`)
- `--temp` / `--max-tokens`
- `--show-tokens` : prints integer token count for the prompt

---

## 🖥 Streamlit UI

Run a modern UI to compare variants and inspect each **rendered prompt**.

```bash
pip install streamlit     # if not installed yet
streamlit run ./streamlit_app.py
```

What you’ll get:
- **Welcome modal** with a friendly GENAI mascot (animated wander → center)
- **Variants** multi‑select (baseline / rubric / fewshot / json_classify)
- **Cases** dropdown (from `data/cases.json`)
- Editable input, sliders for temperature & max tokens
- Output cards with tabs: **Response**, **Rendered prompt**, **Metrics**, **Download**
- Prompt & output token counts, plus CSV/JSON downloads

> Tip: If you ever get an API key error in the UI, ensure `.env` contains `GOOGLE_API_KEY=...` and restart Streamlit.

---

## 🧪 Evaluation Harness

Run all variants across all cases and write CSV/JSON artifacts:

```bash
python ./eval/run_eval.py
```

Outputs:
- `artifacts/results.csv` – easy to sort/filter
- `artifacts/results.json` – raw structured results

**Scoring (simple, transparent)**
- **Summaries**
  - `score_len`: 1.0 if within `max_words` (linear penalty if over)
  - `score_keywords`: fraction of required keywords present
  - `total_score` = average of the two
- **Classification**
  - `ok_json`: 1.0 if valid JSON with expected keys
  - `score_label`: 1.0 if label matches expected
  - `total_score` = average of the two

These are quick guardrails for **prompt iteration**, not absolute accuracy metrics.

---

## 🧩 Prompt Variants & Cases

All variants live in **`prompts/variants.yaml`**. Each has:
- `id`, `title`
- optional `applies_to` (`[summarize, classify]`)
- optional `system` instruction
- `prompt_template` (uses `{task}` and `{input}`)
- optional `few_shots` (inline examples)
- optional `response_mime_type` (e.g., `application/json`)

Cases live in **`data/cases.json`** and look like:

```json
{
  "id": "sum_1",
  "type": "summarize",
  "task": "Summarize the following in one sentence.",
  "input": "The product launch moved from Sep 30 to Oct 7 due to QA issues.",
  "max_words": 25,
  "keywords": ["launch", "Oct 7"]
}
```

---

## ➕ Add Your Own Variant

Append a new block to `prompts/variants.yaml`, e.g.:

```yaml
- id: grounded
  title: Grounded w/ Search (citations)
  applies_to: [summarize]
  system: |-
    You are a precise assistant. Cite sources.
  prompt_template: |-
    Answer briefly and cite sources.
    Question:
    {input}
```

> You can also extend `genai_client.py` to enable Google Search grounding via SDK tools, then use it in this variant.

---

## 🧠 Design Notes (Explain Like I’m Five)

- **Cases** = small tasks (summarize/classify).
- **Variants** = different ways to ask the model (baseline, rules/rubric, example‑driven, JSON‑only).
- **UI** = pick a case + variant(s), click **Run**, and see the answer **and** the exact prompt we sent.
- **Eval** = run everything automatically and write a CSV so you can compare and improve.

> In one line: this repo proves you can **design, run, and measure** prompts — not just chat.

---

## 🧯 Troubleshooting

**`gpl : not recognized`**  
Venv not active or console script not installed. Run:
```bash
source .venv/bin/activate      # or .\.venv\Scripts\Activate.ps1 on Windows
pip install -e .
gpl --help
```

**Auth errors / missing key**  
Ensure `.env` contains `GOOGLE_API_KEY=...`. You can also set it just for this shell:
```bash
export GOOGLE_API_KEY="your_real_key"   # PowerShell: $env:GOOGLE_API_KEY='...'
```

**`ModuleNotFoundError: prompt_lab`**  
Reinstall in editable mode: `pip install -e .`

**Windows PowerShell here‑strings show `>>` prompts**  
Save the snippet to a `.py` file and run `python file.py`, or ensure the here‑string closing `'@` is at **column 1** (no spaces).

**JSON/YAML encoding issues**  
This repo reads with `utf‑8‑sig` to tolerate BOM. If editing on Windows Notepad, prefer UTF‑8 (no BOM).

---

## 🗺 Roadmap

- Add a **grounded** variant (Google Search tool + citations)
- Add **schema‑validated JSON** outputs for structured tasks
- Expand **cases** (longer texts, harder constraints)
- Side‑by‑side UI compare view + export to CSV

---

## 📄 License

MIT. See `LICENSE`.

---

🙌 Credits & documentation

Google GenAI SDK (google-genai)
Overview & Quickstart — https://ai.google.dev/gemini-api/docs

Text generation — https://ai.google.dev/gemini-api/docs/text-generation

Counting tokens — https://ai.google.dev/gemini-api/docs/tokens

Python SDK (PyPI) — https://pypi.org/project/google-genai/

Google AI Studio (API keys & console) — https://aistudio.google.com/

Streamlit (UI framework)
Docs — https://docs.streamlit.io/

Appearance & Theming — https://docs.streamlit.io/develop/concepts/design/streamlit-appearance

Typer (CLI framework) — https://typer.tiangolo.com/

Rich (console formatting) — https://rich.readthedocs.io/

PyYAML (YAML parsing) — https://pyyaml.org/wiki/PyYAMLDocumentation

python-dotenv (env loading) — https://pypi.org/project/python-dotenv/

Packaging / editable installs — https://packaging.python.org/en/latest/tutorials/installing-packages/#installing-from-a-local-src-tree

YAML spec — https://yaml.org/spec/

Icons/emoji — Unicode / Twemoji
