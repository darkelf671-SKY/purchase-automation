# CTO Lead Agent Memory

## Project: 구매기안 자동화 시스템

### Key Architecture
- Python 3 + tkinter desktop app
- HWP COM automation via win32com (`HWPFrame.HwpObject`)
- SQLite3 database
- Core file: `E:\ClaudeCode\purchase-automation\documents\hwp_generator.py`

### HWP COM API Critical Knowledge
- **AllReplace**: Global replace, does NOT move cursor
- **FindReplace**: Finds first match from cursor position, DOES move cursor to match
- **FindReplace Direction=0**: Forward only (from cursor position onward)
- **MoveDocBegin**: Resets cursor to document start -- MUST call before FindReplace
- **TableDeleteRow**: Deletes row at CURRENT cursor position
- **HParameterSet.HFindReplace**: Shared instance, state persists between calls -- always reinitialize

### Active PDCA: hwp-cursor-management-bugfix
- Phase: Plan (completed 2026-03-09)
- 4 bugs identified in cursor management
- Fix strategy: AllReplace -> FindReplace+MoveDocBegin for cursor-dependent operations
- New utility: `_find_and_move_cursor(hwp, target, consume=True)`
- Risk: FindReplace replaces text -- use `consume=False` (ReplaceString=target) for style-only operations (Bug 4)

### Project Structure
- CLAUDE.md: Comprehensive project documentation at root
- No git repo initialized
- No existing PDCA docs before this session
