# Gap Detector Memory - purchase-automation

## Project Profile
- Python 3 desktop app (tkinter) for public procurement document generation
- HWP (win32com) + Excel (openpyxl) + SQLite3
- Design spec lives in CLAUDE.md (no separate design docs)
- 6 tabs: 구매조사, 검수입력, 이력조회, 업체관리, 수의계약사유, 기안템플릿
- 6 DB tables: purchases, purchase_items, vendors, inspections, sole_contract_reasons, draft_templates

## Last Analysis: 2026-03-11 (3rd full analysis)
- Feature: full-project re-verification (10-category deep check)
- Overall match rate: 98% (up from 97%)
- Output: `E:\ClaudeCode\purchase-automation\docs\03-analysis\purchase-automation.analysis.md`
- Design docs: project CLAUDE.md is highly accurate
- Previous gaps (DraftDialog, tab count, typo) all fixed
- Remaining gaps (5):
  - G1: build_exe.py not in project structure tree (Low)
  - G2-G3: SPACING/FONTS doc lists subset of actual tokens (Low)
  - G4: apply_theme(root) should be apply_theme(style) (Low)
  - G5: Root CLAUDE.md (E:\ClaudeCode\CLAUDE.md) severely outdated -- 5tabs, 5tables, old payment logic (Medium)

## Key Patterns
- HWP uses AllReplace action (never FindReplace)
- Multi-item indexed placeholders: {{ITEM_01}} ~ {{ITEM_15}}, MAX_ITEM_ROWS=15
- _search_var pattern used in 5 tabs (inspection, history, vendor, sole_contract, draft_template -- NOT tab_purchase)
- Vendor auto-linking: _vendor_records[] -> _draft_vendor_var.set()
- BaseDialog used by: OutputSettingsDialog, VendorDialog, SoleContractDialog, DraftTemplateDialog, SaveAsTemplateDialog
- design_system.py: COLORS(19), SPACING(6), FONTS(6), apply_theme()
- Watermark on screenshots: _add_timestamp_watermark() applied to capture() and capture_region()
- Inspection UI simplified: has_defect/defect_note always False/"" (DB columns retained)
