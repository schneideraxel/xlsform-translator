### Command-line interface : argument parsing, orchestration, and user-facing output
### AS 🐚🫧🪼🪸
### 05.04.2026 (Last update)

"""
CLI entry point for xlsform-translator.

Invoked as:
    python main.py <input_file> -s <source> -t <target> -e <engine> [options]

Or, if installed as a package:
    xlsform-translator <input_file> -s <source> -t <target> -e <engine> [options]
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .parser import parse_form
from .engines import get_engine, ENGINES
from .writer import build_output


def build_default_output_path(input_path: str, target_language: str) -> str:
    """
    Generate the default output file path when --output is not specified.

    Takes the first word of the target language and appends it to the input
    stem, e.g. survey.xlsx + "Spanish" → survey_spanish.xlsx.
    """
    p = Path(input_path)
    lang_slug = target_language.strip().split()[0].lower()
    return str(p.parent / f"{p.stem}_{lang_slug}{p.suffix}")


def run(argv=None):
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Translate an XLSForm Excel file to a new language."
    )
    parser.add_argument("input_file", help="Path to the source XLSForm .xlsx file")
    parser.add_argument(
        "--source-language", "-s",
        required=True,
        help='Source language of the form, e.g. "French", "English". '
             'Must match a language already present in the column headers '
             '(e.g. the form must have columns like label::French).',
    )
    parser.add_argument(
        "--target-language", "-t",
        required=True,
        help='Target language, e.g. "French", "Swahili", "Spanish"',
    )
    parser.add_argument(
        "--engine", "-e",
        required=True,
        choices=ENGINES,
        help=f"Translation engine to use: {', '.join(ENGINES)}",
    )
    parser.add_argument(
        "--context", "-c",
        default="",
        help=(
            'Optional domain context to improve translation quality, e.g. '
            '"Agricultural survey for rural farmers in Senegal". '
            'Supported by LLM engines (claude, openai) only.'
        ),
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path (default: <input>_<lang>.xlsx)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print progress details",
    )
    args = parser.parse_args(argv)

    if not os.path.isfile(args.input_file):
        print(f"Error: file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    if not args.input_file.lower().endswith(".xlsx"):
        print("Error: input file must be a .xlsx file", file=sys.stderr)
        sys.exit(1)

    output_path = args.output or build_default_output_path(args.input_file, args.target_language)

    import time
    start = time.time()

    engine = get_engine(args.engine)

    print(f"Engine:  {args.engine}")
    if args.context:
        print(f"Context: {args.context}")
    print(f"Parsing: {args.input_file}")

    try:
        parsed = parse_form(args.input_file, args.source_language)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Source language detected: {parsed.source_language}")
    print(f"Translatable cells found: {len(parsed.cells)}")

    if not parsed.cells:
        print("No translatable content found. Exiting.")
        sys.exit(0)

    print(f"Translating to: {args.target_language}")
    warnings = engine.translate_all(
        parsed.cells,
        args.target_language,
        context=args.context,
        verbose=args.verbose,
    )

    print(f"Writing output: {output_path}")
    cells_written = build_output(
        parsed,
        parsed.cells,
        args.target_language,
        output_path,
        verbose=args.verbose,
    )

    elapsed = time.time() - start
    print(f"\nDone. {cells_written} cells translated in {elapsed:.1f}s.")
    if warnings:
        print(f"Warnings: {warnings} cells could not be translated and kept their source text.")
