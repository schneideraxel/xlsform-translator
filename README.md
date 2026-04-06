# xlsform-translator

Translate your survey form into any language in just a few seconds!

A command-line tool that connects to your prefered AI (Claude, OpenAI, Google Translate, DeepL, Azure Translato) and translates XLSForm survey files using AI. It reads an Excel-based XLSForm, translates all user-facing text columns into a target language, and writes a new Excel file with the added language columns.

Compatible with SurveyCTO, ODK Collect, and ArcGIS Survey123. Other data collection environments relying on XLSForm should be compatible.

**Notes**: 
- AI translation is a first draft, always have a fluent speaker review and validate the translated form before deployment.\
- Requires an API key from your chosen translation engine


---

## Features

- Translates `label`, `hint`, `guidance_hint`, `constraint_message`, and `required_message` columns in both `survey` and `choices` sheets
- Supports five translation engines: Claude, OpenAI, Google Translate, DeepL, and Azure Translator
- Preserves XLSForm variable references (`${variable}`), HTML tags, and other non-translatable content automatically
- Validates every translated batch and retries automatically on failure; falls back to source text if all retries are exhausted so the output file is always complete
- Optional domain context to improve translation quality on LLM-based engines

---

## Requirements

- Python 3.9+
- An XLSForm where language columns already include language names in the header, eg: `label::French` or `label::French (fr)`

---

## Installation

```bash
git clone https://github.com/schneideraxel/xlsform-translator.git
cd xlsform-translator
python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Then install the package for the engine you want to use:

```bash
pip install anthropic # Claude
pip install openai # OpenAI
pip install deepl # DeepL
# Google Translate and Azure use requests, which is already included
```

---

## Configuration

Create a `.env` file at the project root. Only the key for your chosen engine is required:

```
ANTHROPIC_API_KEY= ...
OPENAI_API_KEY= ...
GOOGLE_TRANSLATE_API_KEY= ...
DEEPL_API_KEY= ...
AZURE_TRANSLATOR_KEY= ...
AZURE_TRANSLATOR_REGION=eastus
```

---

## Usage

```bash
python main.py <input_file> \
  --source-language <source> \
  --target-language <target> \
  --engine <engine> \
  [--context "<domain context>"] \
  [--output <output_file>] \
  [--verbose]
```

### Arguments

| Argument | Short | Required | Description |
|---|---|---|---|
| `input_file` | | ✓ | Path to the source XLSForm `.xlsx` file |
| `--source-language` | `-s` | ✓ | Language of the source columns, e.g. `French`, `fr` |
| `--target-language` | `-t` | ✓ | Language to translate into, e.g. `English`, `Wolof` |
| `--engine` | `-e` | ✓ | Translation engine: `claude`, `openai`, `google`, `deepl`, `azure` |
| `--context` | `-c` | | Domain context to guide LLM engines (claude, openai only) |
| `--output` | `-o` | | Output file path (default: `<input>_<lang>.xlsx`) |
| `--verbose` | `-v` | | Print per-batch progress and warnings |

### Examples

```bash
# Translate a French SurveyCTO form to English using Claude
python main.py survey.xlsx -s French -t English -e claude

# Translate to Swahili using DeepL, with a custom output path
python main.py survey.xlsx -s French -t Swahili -e deepl -o survey_sw.xlsx

# Use domain context with OpenAI to improve terminology accuracy
python main.py survey.xlsx -s French -t Arabic -e openai -c "Health survey for rural communities in West Africa"

# Translate using a language code instead of a full name
python main.py survey.xlsx -s fr -t en -e google --verbose
```

---

## XLSForm requirements

Your form's columns must already include language names*in the header.

| Accepted ✓ | Rejected ✗ |
|---|---|
| `label::French (fr)` | `label` |
| `label::French` | `hint` |
| `hint::English (en)` | `required_message` |

If your form only has plain column names, rename them to include the language before using this tool: for example, rename `label` to `label::French (fr)`.

---

## How AI engines are used

The role of AI in this tool is deliberately narrow. The program does not ask the AI to interpret, summarise, or reason about your form. It simply sends batches of plain strings to the translation API and receives translated strings back, the same way you would use a translation service manually, just automated and at scale. The process uses very few tokens.

Specifically:
- **No content is generated** : the AI only translates what is already there
- **XLSForm logic is never touched** : skip logic, constraints, calculations, and variable references are extracted before translation and restored verbatim afterwards
- **Every response is validated locally** : the program checks that the number of strings matches, that no translations are empty, and that all protected tokens (`${variable}`, HTML tags) are intact. If any check fails, the batch is retried; if retries are exhausted, the original source text is kept
- **No hallucination risk on form logic** : because variable references and tags are replaced with neutral tokens (e.g. `[P1]`) before being sent to the AI, there is nothing for the model to misinterpret or fabricate

The AI's only job is the translation of human-readable text. Everything else is handled locally in Python.

---

## Supported translation engines

### Claude (`claude`)
Uses Anthropic's **Claude Haiku** model. LLM-based, understands context and produces natural, fluent translations.

Supports the optional `--context` argument, which lets you describe the survey domain (e.g. *"Agricultural baseline survey for smallholder farmers in Senegal"*). This is passed as a system-level instruction and improves terminology choices throughout the translation.

**Languages:** Any language Claude has been trained on: covers all major world languages as well as many regional and lower-resource ones.

---

### OpenAI (`openai`)
Uses **GPT-4o Mini** model. LLM-based, context-aware, produces clear and natural language, and supports the `--context` argument. 

**Languages:** Any language GPT has been trained on: covers all major world languages as well as many regional and lower-resource ones.

---

### Google Translate (`google`)
Uses the **Google Cloud Translation API v2**. A dedicated, high-throughput translation service with very broad language support. Does not understand context. Does **not** support the `--context` argument. Generous free-tier!

**Languages:** 135 languages, including many African languages (Hausa, Yoruba, Igbo, Amharic, Somali, Swahili, Zulu, and more). Check the [full list](https://cloud.google.com/translate/docs/languages).

---

### DeepL (`deepl`)
Uses the **DeepL Translation API**. Widely considered the most accurate dedicated translation service for European languages. Does **not** support the `--context` argument.

**Languages:** 33 languages, primarily European (English, French, Spanish, German, Italian, Portuguese, Dutch, Polish, Russian, Japanese, Chinese, and others). Check the [full list](https://support.deepl.com/hc/en-us/articles/360019925219).

---

### Azure Translator (`azure`)
Uses the **Azure Cognitive Services Translator v3** REST API. Microsoft's dedicated translation service, competitive with Google Translate in breadth of language support. Requires both an API key and a region identifier in your `.env` file.

Does **not** support the `--context` argument.

**Languages:** 130 languages. Check the [full list](https://learn.microsoft.com/en-us/azure/ai-services/translator/language-support).

---

## License

MIT
