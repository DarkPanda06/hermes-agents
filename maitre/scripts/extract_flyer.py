"""Flyer → structured event extraction (T2 ingestion showcase).

In production Maitre ingests events from three messy sources — listings pages,
Instagram flyers, and WhatsApp forwards. Flyers/forwards go through a vision model
with the prompt below, which returns an event in the SAME schema as a seed event,
so it flows straight into the fit scorer.

The demo does NOT run live OCR/vision (no API keys, no network — see README
"What's real vs. stubbed"). Instead this script shows the exact extraction prompt
and a pre-extracted example (maitre/data/flyer_example.json), then runs the real
fit scorer on the extracted event so you can see ingestion → judgment end to end.

Run:  python -m maitre.scripts.extract_flyer
      python -m maitre.scripts.extract_flyer path/to/flyer.png   # falls back to the example
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from maitre import db, loader, fit

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
EXAMPLE_JSON = DATA_DIR / "flyer_example.json"
EXAMPLE_TXT = DATA_DIR / "flyer_example.txt"

# The exact prompt a vision model receives. Kept here so the extraction contract
# is auditable even though the demo doesn't call a model.
EXTRACTION_PROMPT = """\
You are Maitre's ingestion agent. Read this event flyer (image) and return ONE
JSON object matching this schema — nothing else:

  {
    "id": "ev_<slug>",                 // stable slug from title+date
    "title": str,
    "venue": str,
    "area": str,                       // neighbourhood, not full address
    "dt": "YYYY-MM-DDTHH:MM:SS",       // local start time; infer the year if omitted
    "price_min": number,               // INR; 0 if free; lowest tier
    "price_max": number,               // INR; = price_min if single price
    "genre_tags": [str],               // e.g. jazz, techno, comedy, supper_club, edm
    "vibe_tags":  [str],               // e.g. intimate, seated, listening, rave, massive
    "capacity_class": "intimate|mid|massive",   // infer from seats/venue language
    "source": "instagram|whatsapp|listings",
    "url": str
  }

Rules: infer capacity_class from cues ("40 seats only" -> intimate; "3000 cap" ->
massive). Never invent a price — use 0 and note "price_unknown" in a tag if absent.
Return strict JSON, no prose."""


def extract(image_path: str | None) -> dict:
    """Extract a structured event from a flyer.

    Live vision is stubbed in the demo: we return the documented pre-extracted
    example. The signature is the real one a vision backend would implement.
    """
    payload = json.loads(EXAMPLE_JSON.read_text(encoding="utf-8"))
    return payload["event"]


def main() -> None:
    ap = argparse.ArgumentParser(description="Flyer -> event extraction (demo: stubbed vision).")
    ap.add_argument("image", nargs="?", default=str(DATA_DIR / "flyer_example.png"),
                    help="path to a flyer image (falls back to the bundled example)")
    args = ap.parse_args()

    print("=" * 78)
    print("MAITRE · flyer ingestion showcase  (STUBBED vision — pre-extracted example)")
    print("=" * 78)
    print(f"\nInput flyer: {args.image}")
    if Path(args.image).name == "flyer_example.png" or not Path(args.image).exists():
        print("(no live OCR in the demo — using the transcribed example below)\n")
        print(EXAMPLE_TXT.read_text(encoding="utf-8"))

    print("\n--- extraction prompt sent to the vision model -------------------------------")
    print(EXTRACTION_PROMPT)

    event = extract(args.image)
    print("\n--- structured event returned ------------------------------------------------")
    print(json.dumps(event, indent=2, ensure_ascii=False))

    # Prove it flows into the same judgment pipeline as every other event.
    conn = db.reset(":memory:")
    loader.load_seed(conn)
    profile = db.get_profile(conn)
    decision = fit.score(event, profile)
    print("\n--- fit scorer verdict on the freshly-ingested event -------------------------")
    print(f"  {decision.verdict.upper()} · {decision.fit_pct}% fit")
    print(f"  why: {decision.one_liner}")
    conn.close()
    print("\nIngestion → judgment, same schema, no special-casing.\n")


if __name__ == "__main__":
    main()
