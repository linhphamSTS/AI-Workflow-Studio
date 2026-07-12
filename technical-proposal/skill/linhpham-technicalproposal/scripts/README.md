# Scripts

Python helpers invoked by the skill at runtime.

| File | Purpose |
|---|---|
| `build_docx.py` | Assemble final .docx from `proposal_template.docx` + replacements + diagrams |
| `build_diagram.py` | Entry point for diagram rendering (reads spec.json, switches icon pack) |
| `format_reviewer.py` | Strict format + SharePoint compat check on output .docx |
| `auto_fix.py` | Apply auto-fixable patches surfaced by format_reviewer |
| `render_pages.py` | docx -> pdf -> per-page png (LibreOffice headless + pdf2image) |
| `readers/pdf_reader.py` | Extract text from .pdf |
| `readers/docx_reader.py` | Extract text from .docx |
| `readers/doc_reader.py` | Convert .doc to .docx via LibreOffice headless, then read |
| `readers/text_reader.py` | Read .txt / .md |

> Scaffold only — implementation pending.
