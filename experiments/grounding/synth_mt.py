"""Round 10 (H18): synthesize non-English negatives by translating English negatives.

The shipped cross-lingual fix is a threshold patch over English-trained weights - the
weights see only 139 real non-English negatives across 16 languages. This manufactures
more: translate English negatives (VitaminC REFUTES + gold v2 English hallucinations) into
the target languages via `claude -p`, keep the English evidence, verify the translation
preserves meaning, and mark every row synthetic with full provenance. TRAIN-ONLY - the
honest eval never sees synthetic rows.

Reuses the gold_v2.py `claude -p` pattern (env scrubbed of CLAUDE*/ANTHROPIC*, chunked
calls, JSON-from-stdout, retry-to-convergence). Translate with Haiku, verify with Sonnet.

Run from experiments/grounding:
  uv run python synth_mt.py select                          [SYNTH_N=120]
  uv run python synth_mt.py translate --model haiku         [SYNTH_LANGS=nb,sv,...]
  uv run python synth_mt.py verify    --model sonnet
  uv run python synth_mt.py build

Batches: set SYNTH_BATCH=2 (3, ...) to grow the set. select skips every claim used in
prior batches, namespaces intermediates (units.b2.json, ...) and sids (b2s0000, ...);
build globs all batches into the single synthetic_mt.parquet.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess

import pandas as pd

FORENSICS = Path(__file__).resolve().parent / "private-rag-forensics"
GOLD_V2 = FORENSICS / "gold" / "golden_grounding_evidence_v2.parquet"
SYNTH_DIR = FORENSICS / "gold" / "synth"
OUT = FORENSICS / "gold" / "synthetic_mt.parquet"


def _suffix() -> str:
    b = os.environ.get("SYNTH_BATCH", "").strip()
    return f".b{b}" if b else ""


def _sid_prefix() -> str:
    b = os.environ.get("SYNTH_BATCH", "").strip()
    return f"b{b}s" if b else "s"


def _units_path() -> Path:
    return SYNTH_DIR / f"units{_suffix()}.json"


def _transl_path() -> Path:
    return SYNTH_DIR / f"translations{_suffix()}.json"


def _verify_path() -> Path:
    return SYNTH_DIR / f"verify{_suffix()}.json"

# argos can back-translate these at inference (the r1_mt bridge), so the synthetic
# negatives train the same feature distribution production sees. Thin tail first.
TARGET_LANGS = ["sv", "nl", "da", "de", "nb", "it", "pt", "es", "fr"]
CHUNK = 20

_TRANSLATE_PROMPT = """Translate each numbered English claim into {lang_name} ({lang}).
Preserve meaning EXACTLY - every number, unit, date, proper noun, product/part code, and
the polarity (do not negate or un-negate). Keep codes and identifiers verbatim. Output ONLY
a JSON array, one object per claim: [{{"idx": 1, "translation": "..."}}]. There are exactly
{n} claims, numbered 1 to {n}.

Claims:
{claims}"""

_VERIFY_PROMPT = """You verify machine translations for a grounding dataset. For each item
you get an English claim and its {lang_name} translation. Mark "faithful": true ONLY if the
translation preserves the EXACT meaning - same numbers, units, dates, entities, product/part
codes, and the same polarity (negation not added or removed). Any drift that could change
whether the claim is supported by evidence -> false.

Output ONLY a JSON array, one object per item: [{{"idx": 1, "faithful": true}}]. There are
exactly {n} items, numbered 1 to {n}.

Items:
{items}"""

_LANG_NAME = {"sv": "Swedish", "nl": "Dutch", "da": "Danish", "de": "German", "nb": "Norwegian",
              "it": "Italian", "pt": "Portuguese", "es": "Spanish", "fr": "French"}


def _env() -> dict:
    return {k: v for k, v in os.environ.items()
            if not (k.startswith("ANTHROPIC") or k.startswith("CLAUDE"))}


def _claude_json(prompt: str, model: str, env: dict) -> list | None:
    try:
        r = subprocess.run(["claude", "-p", "--model", model, prompt],
                           capture_output=True, text=True, timeout=600, env=env)
        txt = r.stdout.strip()
        start, end = txt.find("["), txt.rfind("]")
        return json.loads(txt[start:end + 1])
    except Exception:
        return None


# ------------------------------------------------------------------------ select
def _vitaminc_refutes() -> list[dict]:
    from huggingface_hub import hf_hub_download

    p = hf_hub_download("tals/vitaminc", "dev.jsonl", repo_type="dataset")
    out = []
    for line in open(p, encoding="utf-8"):
        rec = json.loads(line)
        if rec.get("label") == "REFUTES":
            out.append({"claim": rec["claim"], "source_text": rec["evidence"],
                        "source_corpus": "vitaminc"})
    return out


def cmd_select() -> None:
    cap = int(os.environ.get("SYNTH_N", "120"))
    df = pd.read_parquet(GOLD_V2)
    df["base"] = df["lang"].astype(str).str.split("-").str[0].str.lower()
    gold_neg = [
        {"claim": r["claim"], "source_text": r["source_text"], "source_corpus": "gold_v2"}
        for r in df[(df.label == 0) & (df.base == "en")].to_dict("records")
    ]
    pool = gold_neg + _vitaminc_refutes()
    # claims used by other batches - skip them so each batch is a fresh slice
    mine = _units_path()
    seen = set()
    for up in SYNTH_DIR.glob("units*.json"):
        if up == mine:
            continue
        for u in json.loads(up.read_text()):
            seen.add(u["claim"].strip().lower())
    # dedup by claim, cap, stable order (no Math.random - slice deterministically)
    prefix, units = _sid_prefix(), []
    for i, r in enumerate(pool):
        k = r["claim"].strip().lower()
        if k in seen or len(r["claim"].strip()) < 20:
            continue
        seen.add(k)
        units.append({"sid": f"{prefix}{len(units):04d}", **r})
        if len(units) >= cap:
            break
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    mine.write_text(json.dumps(units, ensure_ascii=False))
    n_gold = sum(1 for u in units if u["source_corpus"] == "gold_v2")
    print(f"selected {len(units)} English negatives ({n_gold} gold_v2 + "
          f"{len(units) - n_gold} vitaminc), cap {cap}")


# --------------------------------------------------------------------- translate
def _do_lang(units: list[dict], lang: str, model: str, env: dict) -> tuple[str, dict]:
    out: dict[str, str] = {}
    for off in range(0, len(units), CHUNK):
        sub = units[off:off + CHUNK]
        numbered = "\n".join(f"{i}. {u['claim']}" for i, u in enumerate(sub, 1))
        prompt = _TRANSLATE_PROMPT.format(lang=lang, lang_name=_LANG_NAME[lang],
                                          n=len(sub), claims=numbered)
        res = _claude_json(prompt, model, env)
        if res is None:
            continue
        for rec in res:
            idx = rec.get("idx", 0)
            if 1 <= idx <= len(sub) and rec.get("translation"):
                out[sub[idx - 1]["sid"]] = rec["translation"].strip()
    return lang, out


def cmd_translate(model: str, workers: int) -> None:
    transl = _transl_path()
    units = json.loads(_units_path().read_text())
    langs = os.environ.get("SYNTH_LANGS", ",".join(TARGET_LANGS)).split(",")
    done = json.loads(transl.read_text()) if transl.exists() else {}
    env = _env()
    todo = [lg for lg in langs if lg not in done]
    print(f"translate {len(units)} claims x {len(todo)} langs ({model})")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_do_lang, units, lg, model, env): lg for lg in todo}
        for f in as_completed(futs):
            lang, out = f.result()
            done[lang] = out
            transl.write_text(json.dumps(done, ensure_ascii=False))
            print(f"  {lang}: {len(out)}/{len(units)} translated", flush=True)


# ------------------------------------------------------------------------ verify
def _verify_lang(units: list[dict], lang: str, trans: dict, model: str,
                 env: dict) -> tuple[str, dict]:
    by_sid = {u["sid"]: u for u in units}
    items = [(sid, by_sid[sid]["claim"], t) for sid, t in trans.items() if sid in by_sid]
    out: dict[str, bool] = {}
    for off in range(0, len(items), CHUNK):
        sub = items[off:off + CHUNK]
        block = "\n".join(f'{i}. EN: {c}\n   {_LANG_NAME[lang]}: {t}'
                          for i, (_, c, t) in enumerate(sub, 1))
        prompt = _VERIFY_PROMPT.format(lang_name=_LANG_NAME[lang], n=len(sub), items=block)
        res = _claude_json(prompt, model, env)
        if res is None:
            continue
        for rec in res:
            idx = rec.get("idx", 0)
            if 1 <= idx <= len(sub):
                out[sub[idx - 1][0]] = bool(rec.get("faithful"))
    return lang, out


def cmd_verify(model: str, workers: int) -> None:
    verify = _verify_path()
    units = json.loads(_units_path().read_text())
    trans = json.loads(_transl_path().read_text())
    done = json.loads(verify.read_text()) if verify.exists() else {}
    env = _env()
    todo = [lg for lg in trans if lg not in done]
    print(f"verify {len(todo)} langs ({model})")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_verify_lang, units, lg, trans[lg], model, env): lg for lg in todo}
        for f in as_completed(futs):
            lang, out = f.result()
            done[lang] = out
            verify.write_text(json.dumps(done, ensure_ascii=False))
            kept = sum(1 for v in out.values() if v)
            print(f"  {lang}: {kept}/{len(out)} faithful", flush=True)


# ------------------------------------------------------------------------- build
def cmd_build(translator: str, verifier: str) -> None:
    rows, batches = [], 0
    for upath in sorted(SYNTH_DIR.glob("units*.json")):
        tpath = upath.with_name(upath.name.replace("units", "translations"))
        vpath = upath.with_name(upath.name.replace("units", "verify"))
        if not (tpath.exists() and vpath.exists()):
            continue
        batches += 1
        units = {u["sid"]: u for u in json.loads(upath.read_text())}
        trans = json.loads(tpath.read_text())
        verify = json.loads(vpath.read_text())
        for lang, by_sid in trans.items():
            vmap = verify.get(lang, {})
            for sid, translation in by_sid.items():
                if sid not in units or not vmap.get(sid):
                    continue  # drop unverified / drifted
                u = units[sid]
                rows.append({
                    "claim": translation, "source_text": u["source_text"], "label": 0,
                    "lang": lang, "trace_id": f"synth_{u['source_corpus']}_{sid}",
                    "origin": "synthetic_mt", "source_sid": sid,
                    "source_corpus": u["source_corpus"], "source_lang": "en",
                    "target_lang": lang, "translator_model": translator,
                    "verifier_model": verifier, "verified": True,
                    "verify_method": "claude_p_equivalence",
                })
    df = pd.DataFrame(rows)
    df.to_parquet(OUT)
    by_lang = df.groupby("target_lang").size().to_dict() if len(df) else {}
    print(f"wrote {len(df)} verified synthetic non-English negatives "
          f"from {batches} batch(es) -> {OUT}")
    print(f"  per language: {by_lang}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["select", "translate", "verify", "build"])
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--translator", default="haiku")
    ap.add_argument("--verifier", default="sonnet")
    a = ap.parse_args()
    if a.cmd == "select":
        cmd_select()
    elif a.cmd == "translate":
        cmd_translate(a.model, a.workers)
    elif a.cmd == "verify":
        cmd_verify(a.model, a.workers)
    else:
        cmd_build(a.translator, a.verifier)
