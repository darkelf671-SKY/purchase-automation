# Code Analyzer Memory - purchase-automation

## Project Structure
- Python 3 tkinter desktop app for public procurement automation
- 5 tabs: Purchase, Inspection, History, Vendor, SoleContract
- HWP/Excel document generation via win32com/openpyxl
- SQLite3 database, multi-item (1:N) purchase structure

## Key Findings (2026-03-10 Analysis)
- See `ui-analysis-2026-03-10.md` for detailed findings
- Quality Score: 62/100
- Main issues: duplicate code (delete_folder_with_retry, search bar, CRUD tabs), 3 unused legacy files, hardcoded API keys

## Architecture Notes
- VAT calculation logic embedded in UI layer (tab_purchase.py ItemRow)
- No service layer between UI and repositories
- Dialog initialization boilerplate repeated 5 times
- tab_purchase.py is 829 lines (2.7x recommended max)

## File Relationships
- `ui/dialog_settings.py` = active settings (output dir)
- `ui/settings_dialog.py` = dead code (API key settings, unused)
- `ui/tab_manual.py`, `ui/tab_auto.py` = legacy, incompatible with current PurchaseData model
