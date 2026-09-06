"""Minimal CLI: analyse one text file with a configured model call.

    echo "text..." | laclaugpt analyse --provider ollama --model gemma3:12b

The provider abstraction is a callable; add providers in one place.
This CLI demonstrates the public API — production pipelines live elsewhere.
"""
from __future__ import annotations

import argparse
import json
import sys


def _ollama_call(model: str):
    def call(system: str, user: str) -> str:
        from ollama import chat
        response = chat(model=model, messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])
        return response["message"]["content"]
    return call


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="laclaugpt")
    parser.add_argument("command", choices=["analyse"], nargs="?", default="analyse")
    parser.add_argument("--file", required=True, help="text file to analyse")
    parser.add_argument("--provider", default="ollama", choices=["ollama"])
    parser.add_argument("--model", default="gemma3:12b")
    parser.add_argument("--source-type", default="source_text",
                        choices=["source_text", "transcript", "ocr", "frame_description"])
    args = parser.parse_args(argv)

    text = open(args.file, encoding="utf-8").read()
    if args.provider == "ollama":
        model_call = _ollama_call(args.model)
    else:  # pragma: no cover
        parser.error(f"unknown provider: {args.provider}")

    from laclaugpt import analyze
    result = analyze(text, model_call=model_call, source_type=args.source_type,
                     model=args.model)
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())