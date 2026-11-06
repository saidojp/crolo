"""Debug CLI: ``python -m apkg.cli path/to/deck.apkg``."""

from __future__ import annotations

import argparse
import json
import sys

from apkg.errors import ApkgError
from apkg.importer import import_apkg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect an Anki .apkg and preview quiz items")
    parser.add_argument("path", help="Path to a .apkg file")
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON")
    parser.add_argument("--limit", type=int, default=20, help="Items to preview")
    args = parser.parse_args(argv)

    try:
        with open(args.path, "rb") as handle:
            result = import_apkg(handle.read(), filename=args.path)
    except OSError as exc:
        print(f"Could not read {args.path}: {exc}", file=sys.stderr)
        return 2
    except ApkgError as exc:
        print(f"[{exc.code}] {exc.message}", file=sys.stderr)
        return 1

    summary = result.summary()
    if args.json:
        print(json.dumps({"summary": summary, "items": [
            {
                "front": item.front,
                "reading": item.reading,
                "meaning": item.meaning,
                "options": item.options,
                "correct_index": item.correct_index,
                "needs_review": item.needs_review,
            }
            for item in result.items
        ]}, ensure_ascii=False, indent=2))
        return 0

    print(f"Deck:        {summary['deck_name']}")
    print(f"Package:     v{summary['package_version']} ({summary['collection_file']}), schema {summary['schema_version']}")
    print(f"Notes:       {summary['total_notes']}")
    print(f"Parsed:      {summary['parsed']}")
    print(f"Items:       {summary['items']} (quiz-ready {summary['quiz_ready']})")
    print(f"Duplicates:  {summary['duplicates']}")
    print(f"Skips:       {summary['skipped']}")
    print(f"Options:     {summary['options']}")
    if summary["plans"]:
        print("Field plans:")
        for name, plan in summary["plans"].items():
            print(f"  {name}: {plan}")
    if summary["ambiguous"]:
        print(f"Ambiguous ({len(summary['ambiguous'])}):")
        for entry in summary["ambiguous"][:10]:
            print(f"  {entry['front']}: {', '.join(entry['readings'])}")
    if summary["warnings"]:
        print("Warnings:")
        for warning in summary["warnings"]:
            print(f"  - {warning}")
    print("\nPreview:")
    for item in result.items[: args.limit]:
        print(f"  {item.front}  →  {item.reading}   [{', '.join(item.options)}]")
        if item.meaning:
            print(f"      {item.meaning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
