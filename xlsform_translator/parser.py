"""
XLSForm parsing: column classification, source language matching,
and placeholder tokenization/detokenization.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

import openpyxl

# Sheets that contain translatable content (order matters: survey first)
TRANSLATABLE_SHEETS = ("survey", "choices")

# Base column names that hold user-facing text
BASE_TRANSLATABLE = {
    "label",
    "hint",
    "guidance_hint",
    "constraint_message",
    "constraint message",
    "required_message",
    "required message",
}

# Matches ${variable}, <html tags>, and #{ODK-style} references
PLACEHOLDER_RE = re.compile(r"\$\{[^}]+\}|<[^>]+>|#\{[^}]+\}")


@dataclass
class ColumnInfo:
    """Describes a column that holds translatable text."""
    name: str        # actual column header string
    base: str        # e.g. "label"
    language: str    # e.g. "French (fr)" or "" for plain columns
    col_index: int   # 1-based column index in the sheet


@dataclass
class CellRef:
    """A reference to a single translatable cell."""
    sheet_name: str
    row: int           # 1-based
    col_index: int     # 1-based
    source_text: str
    tokenized_text: str = ""
    token_map: dict = field(default_factory=dict)  # "[P1]" -> original placeholder


@dataclass
class ParsedForm:
    """Everything extracted from an XLSForm file."""
    workbook: openpyxl.Workbook
    source_language: str      # exact language string matched in column headers
    language_style: str       # "with_code" | "without_code"
    translatable_columns: dict  # sheet_name -> list[ColumnInfo]
    cells: list               # list[CellRef] — all non-empty translatable cells


# ---------------------------------------------------------------------------
# Column classification
# ---------------------------------------------------------------------------

def _classify_column(name: str, col_index: int) -> Optional[ColumnInfo]:
    """
    Returns a ColumnInfo if the column is translatable, else None.
    - Exact match to BASE_TRANSLATABLE → plain column (language = "")
    - base::language pattern where base is in BASE_TRANSLATABLE → language variant
    - Anything else → skip (bind::*, body::*, media::*, etc.)
    """
    if name in BASE_TRANSLATABLE:
        return ColumnInfo(name=name, base=name, language="", col_index=col_index)

    if "::" in name:
        base, _, lang = name.partition("::")
        if base in BASE_TRANSLATABLE:
            return ColumnInfo(name=name, base=base, language=lang, col_index=col_index)

    return None


def classify_columns(sheet) -> list:
    """Return list of ColumnInfo for all translatable columns in a sheet."""
    result = []
    header_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), [])
    for col_index, cell_value in enumerate(header_row, start=1):
        if cell_value is None:
            continue
        info = _classify_column(str(cell_value).strip(), col_index)
        if info:
            result.append(info)
    return result


def _load_translatable_columns(workbook) -> dict:
    result = {}
    for sheet_name in TRANSLATABLE_SHEETS:
        if sheet_name in workbook.sheetnames:
            cols = classify_columns(workbook[sheet_name])
            if cols:
                result[sheet_name] = cols
    return result


def _col_has_content(sheet, col_index: int) -> bool:
    for row in sheet.iter_rows(min_row=2, values_only=True):
        val = row[col_index - 1]
        if val and str(val).strip():
            return True
    return False


# ---------------------------------------------------------------------------
# Source language matching
# ---------------------------------------------------------------------------

def _all_language_variants(translatable_columns: dict) -> set:
    """Return the set of all language strings found in column headers."""
    langs = set()
    for cols in translatable_columns.values():
        for col in cols:
            if col.language:
                langs.add(col.language)
    return langs


def _plain_columns_with_content(workbook, translatable_columns: dict) -> list:
    """Return a list of plain column names that contain non-empty cells."""
    found = []
    for sheet_name in TRANSLATABLE_SHEETS:
        cols = translatable_columns.get(sheet_name, [])
        if not cols:
            continue
        sheet = workbook[sheet_name]
        for col in cols:
            if not col.language and col.name not in found:
                if _col_has_content(sheet, col.col_index):
                    found.append(col.name)
    return found


def _resolve_language_code(language_str: str) -> Optional[str]:
    """
    Extract or resolve an IETF language code from any language string format:
    "French (fr)"  → "fr"   (extract from parentheses)
    "French (FR)"  → "fr"   (uppercase code, normalised to lowercase)
    "French"       → "fr"   (look up by name via langcodes)
    "fr"           → "fr"   (already a code)
    Returns None on failure.
    """
    # Extract code from parentheses, case-insensitive
    m = re.search(r"\(([a-zA-Z]{2,3})\)$", language_str.strip())
    if m:
        return m.group(1).lower()
    try:
        import langcodes
        # Try as an IETF tag first (handles "fr", "sw", "en" etc.)
        try:
            return langcodes.Language.get(language_str.strip()).language.lower()
        except Exception:
            pass
        # Fall back to name lookup ("French", "Swahili" etc.)
        return langcodes.find(language_str.strip()).language.lower()
    except Exception:
        return None


def _match_source_language(translatable_columns: dict, user_language: str) -> Optional[str]:
    """
    Find the language string in the form's column headers that matches the
    user-supplied source language. Returns the exact column language string
    (e.g., "French (fr)") or None if no match is found.

    Matching strategy (in order):
    1. Exact case-insensitive string match
    2. IETF code match (both sides resolved via langcodes)
    """
    available = _all_language_variants(translatable_columns)
    user_lower = user_language.strip().lower()

    # Pass 1: exact case-insensitive match
    for lang in available:
        if lang.strip().lower() == user_lower:
            return lang

    # Pass 2: resolve both sides to IETF codes and compare
    user_code = _resolve_language_code(user_language)
    if user_code:
        for lang in available:
            col_code = _resolve_language_code(lang)
            if col_code and col_code == user_code:
                return lang

    return None


# ---------------------------------------------------------------------------
# Placeholder tokenization
# ---------------------------------------------------------------------------

def tokenize(text: str) -> tuple:
    """
    Replace placeholders with [P1], [P2], ... tokens.
    Returns (tokenized_text, token_map) where token_map maps "[P1]" -> original.
    """
    token_map = {}
    counter = [0]

    def replace(m):
        counter[0] += 1
        token = f"[P{counter[0]}]"
        token_map[token] = m.group(0)
        return token

    tokenized = PLACEHOLDER_RE.sub(replace, text)
    return tokenized, token_map


def detokenize(text: str, token_map: dict) -> str:
    """Restore [P1], [P2], ... tokens back to their original placeholders."""
    for token, original in token_map.items():
        text = text.replace(token, original)
    return text


# ---------------------------------------------------------------------------
# Top-level parse function
# ---------------------------------------------------------------------------

def parse_form(filepath: str, source_language: str) -> ParsedForm:
    """
    Load an XLSForm workbook and collect all translatable cells for the
    given source language.

    Fails with a descriptive error if:
    - The form has no language-variant columns (plain column names only)
    - The specified source language does not match any column in the form
    """
    workbook = openpyxl.load_workbook(filepath)
    translatable_columns = _load_translatable_columns(workbook)

    # Fail if no language-variant columns exist at all
    available_languages = _all_language_variants(translatable_columns)
    if not available_languages:
        plain_with_content = _plain_columns_with_content(workbook, translatable_columns)
        if plain_with_content:
            raise ValueError(
                f"This form has plain columns without a language suffix: "
                f"{', '.join(plain_with_content)}. "
                "Rename your columns to include the language, "
                "e.g. 'label::French (fr)' or 'label::French', "
                "then run the tool again."
            )
        raise ValueError("No translatable content found in this form.")

    # Match source language to a column language string
    matched = _match_source_language(translatable_columns, source_language)
    if not matched:
        raise ValueError(
            f"Source language '{source_language}' not found in this form. "
            f"Available languages: {', '.join(sorted(available_languages))}"
        )

    language_style = (
        "with_code"
        if re.search(r"\([a-z]{2,3}\)$", matched)
        else "without_code"
    )

    # Collect all non-empty cells from the matched source language columns
    cells = []
    for sheet_name in TRANSLATABLE_SHEETS:
        cols = translatable_columns.get(sheet_name, [])
        sheet = workbook[sheet_name]
        source_cols = [c for c in cols if c.language == matched]
        for col_info in source_cols:
            for row_idx, row in enumerate(
                sheet.iter_rows(min_row=2, values_only=True), start=2
            ):
                val = row[col_info.col_index - 1]
                if val is None:
                    continue
                text = str(val).strip()
                if not text:
                    continue
                tokenized, token_map = tokenize(text)
                cells.append(CellRef(
                    sheet_name=sheet_name,
                    row=row_idx,
                    col_index=col_info.col_index,
                    source_text=text,
                    tokenized_text=tokenized,
                    token_map=token_map,
                ))

    return ParsedForm(
        workbook=workbook,
        source_language=matched,
        language_style=language_style,
        translatable_columns=translatable_columns,
        cells=cells,
    )
