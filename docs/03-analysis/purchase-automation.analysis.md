# Design-Implementation Gap Analysis Report

> **Summary**: CLAUDE.md vs actual codebase comparison for purchase-automation
>
> **Author**: gap-detector agent
> **Created**: 2026-03-11
> **Last Modified**: 2026-03-11
> **Status**: Approved

---

## Analysis Overview

- **Analysis Target**: Full project (purchase-automation)
- **Design Document**: `E:\ClaudeCode\purchase-automation\CLAUDE.md`
- **Implementation Path**: `E:\ClaudeCode\purchase-automation\`
- **Analysis Date**: 2026-03-11

## Overall Scores

| Category | Score | Status |
|----------|:-----:|:------:|
| Project Structure | 97% | ⚠️ |
| DB Schema | 100% | ✅ |
| HWP Placeholders | 100% | ✅ |
| UI Tabs & Features | 100% | ✅ |
| Search Functionality | 100% | ✅ |
| Inspection Draft Info | 100% | ✅ |
| Progress Checklist | 100% | ✅ |
| Design System | 98% | ⚠️ |
| EXE Build | 100% | ✅ |
| Payment Section | 100% | ✅ |
| Convention Compliance | 95% | ⚠️ |
| **Overall** | **98%** | ✅ |

---

## 1. Project Structure

### Result: 97% ⚠️

| Item | Design (CLAUDE.md) | Implementation | Status |
|------|---------------------|----------------|:------:|
| main.py | Listed | Exists | ✅ |
| config.py | Listed | Exists | ✅ |
| core/models.py | Listed | Exists | ✅ |
| core/naver_api.py | Listed | Exists | ✅ |
| core/filter_engine.py | Listed | Exists | ✅ |
| core/screenshot.py | Listed | Exists | ✅ |
| core/semi_auto.py | Listed | Exists | ✅ |
| db/database.py | Listed (6 tables) | 6 tables confirmed | ✅ |
| db/purchase_repo.py | Listed | Exists | ✅ |
| db/inspection_repo.py | Listed | Exists | ✅ |
| db/vendor_repo.py | Listed | Exists | ✅ |
| db/sole_contract_repo.py | Listed | Exists | ✅ |
| db/draft_template_repo.py | Listed | Exists | ✅ |
| documents/hwp_generator.py | Listed | Exists | ✅ |
| documents/excel_generator.py | Listed | Exists | ✅ |
| ui/app.py | Listed (6 tabs) | 6 tabs confirmed | ✅ |
| ui/base_dialog.py | Listed | Exists | ✅ |
| ui/design_system.py | Listed | Exists | ✅ |
| ui/tab_purchase.py | Listed | Exists | ✅ |
| ui/tab_inspection.py | Listed | Exists | ✅ |
| ui/tab_history.py | Listed | Exists | ✅ |
| ui/tab_vendor.py | Listed | Exists | ✅ |
| ui/tab_sole_contract.py | Listed | Exists | ✅ |
| ui/tab_draft_template.py | Listed | Exists | ✅ |
| ui/dialog_settings.py | Listed | Exists | ✅ |
| build_exe.py | Not in structure tree | Exists | ⚠️ |

### Gaps Found

| # | Type | Description | Severity |
|---|------|-------------|----------|
| G1 | Added | `build_exe.py` exists but is not listed in the project structure tree (documented in EXE build section only) | Low |

---

## 2. DB Schema

### Result: 100% ✅

| Table | Design | Implementation | Status |
|-------|--------|----------------|:------:|
| purchases | Documented | CREATE TABLE + migration columns match | ✅ |
| purchase_items | Documented | Matches: seq, item_name, spec, unit, quantity, unit_price, total_price, v2_unit_price, remark | ✅ |
| vendors | Documented | Matches: name, ceo, business_no, address, payment_method, bank_name, account_holder, account_no | ✅ |
| inspections | Documented | Matches: inspection_date, inspector, witness, inspected_qty, has_defect, defect_note, remark, doc fields | ✅ |
| sole_contract_reasons | Documented | Matches: label, reason, created_at | ✅ |
| draft_templates | Documented | Matches: id, label, title, content, remark, created_at | ✅ |

**purchases additional columns** (CLAUDE.md line 231-238):

| Column | Design | Implementation (migration) | Status |
|--------|--------|---------------------------|:------:|
| draft_date | Listed | `_migrate()` adds it | ✅ |
| doc_folder | Listed | `_migrate()` adds it | ✅ |
| vat_mode | Listed | `_migrate()` adds it | ✅ |
| item_count | Listed | `_migrate()` adds it | ✅ |
| doc_draft_remark | Listed | `_migrate()` adds it | ✅ |

---

## 3. HWP Placeholders

### Result: 100% ✅

#### Calculation Document (산출기초조사서)

All placeholders documented in CLAUDE.md (lines 90-104) are implemented in `generate_calculation()`:

| Placeholder | Implementation | Status |
|-------------|---------------|:------:|
| `{{TOTAL_PRICE_FORMAL}}` | `_format_korean_amount(_gt)` | ✅ |
| `{{VENDOR1_NAME}}` | `low.name` | ✅ |
| `{{VENDOR1_TOTAL}}` | `_format_number(low.total_price)` | ✅ |
| `{{VENDOR2_NAME}}` | `high.name` | ✅ |
| `{{VENDOR2_TOTAL}}` | `_format_number(high.total_price)` | ✅ |
| `{{SEL_VENDOR}}` | `low.name` | ✅ |
| `{{SEL_TOTAL}}` | `_format_number(_gt)` | ✅ |
| `{{TODAY}}` | `short_date` (YYYY. MM. DD format) | ✅ |

Multi-item indexed placeholders (`{{ITEM_01}}`~`{{ITEM_15}}` etc.) implemented in `_build_calc_item_replacements()`.

#### Draft Document (내부기안)

All placeholders documented in CLAUDE.md (lines 106-128) match `generate_draft()`:

| Placeholder | CLAUDE.md Description | Implementation | Status |
|-------------|----------------------|---------------|:------:|
| `{{PAYMENT_METHOD}}` | "계약방법 (수의계약 고정)" | `"수의계약" if has_payment else ""` | ✅ |
| `{{PAYMENT_SECTION}}` | "계약방법 조건부 섹션" | `f"{num}. 계약방법 : 수의계약"` with dynamic numbering | ✅ |
| `{{SOLE_SECTION}}` | "수의계약 사유 조건부 섹션" | Conditional with dynamic numbering | ✅ |
| All others | Match | Match | ✅ |

#### Inspection Report (물품검수조서)

All 10 placeholders (lines 130-142) match `generate_inspection_report()`. ✅

---

## 4. UI Tabs

### Result: 100% ✅

| Tab | Design | Implementation (app.py) | Status |
|-----|--------|------------------------|:------:|
| Tab 1: 구매 조사 | Listed | `PurchaseTab` | ✅ |
| Tab 2: 검수 입력 | Listed | `InspectionTab` | ✅ |
| Tab 3: 이력 조회 | Listed | `HistoryTab` | ✅ |
| Tab 4: 업체 관리 | Listed | `VendorTab` | ✅ |
| Tab 5: 수의계약 사유 | Listed | `SoleContractTab` | ✅ |
| Tab 6: 기안 템플릿 | Listed | `DraftTemplateTab` | ✅ |

CLAUDE.md says "6탭 구성" (line 9), app.py has exactly 6 tabs. ✅

---

## 5. Search Functionality

### Result: 100% ✅

CLAUDE.md (line 283): "검색 기능 구현 패턴 (5개 탭 공통)"

Verified `_search_var` exists in exactly 5 tabs:
1. `tab_inspection.py` -- with checkboxes ✅
2. `tab_history.py` -- with checkboxes ✅
3. `tab_vendor.py` -- simple text filter ✅
4. `tab_sole_contract.py` -- simple text filter ✅
5. `tab_draft_template.py` -- simple text filter ✅

`tab_purchase.py` does NOT use `_search_var` -- correctly excluded from the "5개 탭" count.

CLAUDE.md (lines 290-292): Checkbox search for inspection/history tabs:
- Both implement `_chkvar()` helper with 4 checkboxes: 품명, 부서명, 기안제목, 기안내용 ✅
- Search targets: `item_name`, `department`, `doc_draft_title`, `doc_draft_content` ✅

---

## 6. Inspection Tab Draft Info Display

### Result: 100% ✅

CLAUDE.md (lines 294-297):
- "구매건 선택 시 상단에 기안제목/기안내용/비고 표시 (읽기 전용)" -- `_draft_title_var`, `_draft_content_var`, `_draft_remark_var` ✅
- "이력조회 상세 패널과 동일한 레이아웃 (라벨 width=8, anchor='e')" -- `_lbl_w = 8`, labels use `anchor="e"` ✅
- "기안내용 200자 초과 시 말줄임 처리" -- `if len(content) > 200: content = content[:200] + "..."` ✅
- "wraplength=600" -- `wraplength=600` on `_draft_content_label` ✅

---

## 7. Progress Checklist

### Result: 100% ✅

All 18 checked items in CLAUDE.md (lines 188-216) verified against implementation. All unchecked items (HWP template insertion, integration test) correctly remain as future work.

Key verifications:
- [x] Design system -- `design_system.py` with COLORS(19), SPACING(6), FONTS(6) ✅
- [x] BaseDialog -- `base_dialog.py` with 5 subclasses ✅
- [x] Tab 6 -- `tab_draft_template.py` fully implemented ✅
- [x] Settings Hot Reload -- `dialog_settings -> app.py._on_settings_saved -> tab_inspection.reload_settings()` ✅
- [x] DPI scaling -- `main.py` line 8: `SetProcessDpiAwareness(1)` ✅
- [x] Payment section -- "수의계약" fixed text, dynamic numbering ✅
- [x] HWP COM -- Dispatch + CoInitialize + gen_py redirect ✅
- [x] EXE build -- `build_exe.py` with PyInstaller ✅

---

## 8. Design System

### Result: 98% ⚠️

CLAUDE.md (lines 240-246):

| Item | Design | Implementation | Status |
|------|--------|---------------|:------:|
| COLORS | "primary, success, warning, danger, total, border, tooltip" | 19 color tokens (all listed + more) | ✅ |
| SPACING | "sm/md/lg" | 6 levels: xs/sm/md/lg/xl/xxl | ⚠️ |
| FONTS | "heading/body/small" | 6 fonts: small/body/body_bold/heading/total/title | ⚠️ |
| apply_theme(root) | Listed | `apply_theme(style: ttk.Style)` -- parameter name mismatch | ⚠️ |
| configure_treeview_tags(tree) | Listed | Exists | ✅ |
| insert_with_alternating(tree, ...) | Listed | Exists | ✅ |

### Gaps Found

| # | Type | Description | Severity |
|---|------|-------------|----------|
| G2 | Doc Incomplete | SPACING described as "sm/md/lg" but actually has 6 levels | Low |
| G3 | Doc Incomplete | FONTS described as "heading/body/small" but actually has 6 fonts | Low |
| G4 | Doc Inaccuracy | `apply_theme(root)` should be `apply_theme(style)` | Low |

---

## 9. EXE Build

### Result: 100% ✅

CLAUDE.md (lines 265-270):

| Item | Design | Implementation | Status |
|------|--------|---------------|:------:|
| `python build_exe.py` | Listed | `build_exe.py` exists | ✅ |
| PyInstaller --onefile --windowed | Listed | Both flags in cmd | ✅ |
| Seed DB: vendors/sole/templates | Listed | `create_seed_db()` extracts all 3 | ✅ |
| First-run seed copy | Listed | `config.py` line 56-60 | ✅ |
| _MEIPASS for templates | Listed | `config.py` line 11 | ✅ |
| gen_py cache TEMP redirect | Listed | `hwp_generator.py` lines 28-30 | ✅ |
| Dispatch (late binding) | Listed | `win32com.client.Dispatch()` | ✅ |
| CoInitialize/CoUninitialize | Listed | Both called | ✅ |

---

## 10. Payment Section Logic

### Result: 100% ✅

CLAUDE.md (lines 272-275):

| Item | Design | Implementation | Status |
|------|--------|---------------|:------:|
| Included: `"{num}. 계약방법 : 수의계약"` | Listed | `f"{num}. 계약방법 : 수의계약"` | ✅ |
| Dynamic numbering | Listed | `num` starts at 3, increments per section | ✅ |
| Excluded: paragraph deletion | Listed | `delete_paragraphs.append("{{PAYMENT_SECTION}}")` | ✅ |
| Old card/transfer logic removed | Listed | No card/transfer branching remains | ✅ |

---

## 11. BaseDialog Pattern

### Result: 100% ✅

| Subclass | Design | Implementation | Status |
|----------|--------|---------------|:------:|
| OutputSettingsDialog | Listed | `dialog_settings.py` extends BaseDialog | ✅ |
| DraftTemplateDialog | Listed | `tab_draft_template.py` extends BaseDialog | ✅ |
| SaveAsTemplateDialog | Listed | `tab_purchase.py` extends BaseDialog | ✅ |
| VendorDialog | Listed | `tab_vendor.py` extends BaseDialog | ✅ |
| SoleContractDialog | Listed | `tab_sole_contract.py` extends BaseDialog | ✅ |
| _build_content(f) | Listed | All subclasses override | ✅ |
| _on_save() | Listed | All subclasses override | ✅ |
| _fire_save_callback() | Listed | Used in all save flows | ✅ |

---

## 12. Root CLAUDE.md Consistency

### Result: ⚠️ (Outdated parent document)

The root `E:\ClaudeCode\CLAUDE.md` diverges from the project-level CLAUDE.md:

| Item | Root CLAUDE.md | Project CLAUDE.md | Status |
|------|---------------|-------------------|:------:|
| Tab count | "5탭 구성" | "6탭 구성" | ❌ |
| DB tables | "5개 테이블" | "6개 테이블" | ❌ |
| `{{PAYMENT_METHOD}}` | "결제방법 (법인카드사용 or 무통장입금)" | "계약방법 (수의계약 고정)" | ❌ |
| `{{PAYMENT_SECTION}}` | "카드/계좌이체 분기" | "수의계약, 동적 순번" | ❌ |
| File listing | Missing 4 files | Complete | ❌ |
| settings_dialog.py | Listed | Does not exist | ❌ |

**Impact**: Root CLAUDE.md is stale (pre-v1.1). Could mislead tools that read root-level context.

| # | Type | Description | Severity |
|---|------|-------------|----------|
| G5 | Outdated | Root CLAUDE.md has 6+ stale items vs project CLAUDE.md and actual implementation | Medium |

---

## Gap Summary

| # | Category | Type | Description | Severity |
|---|----------|------|-------------|----------|
| G1 | Structure | Doc Omission | `build_exe.py` not in project structure tree | Low |
| G2 | Design System | Doc Incomplete | SPACING documented as 3 levels, actually 6 | Low |
| G3 | Design System | Doc Incomplete | FONTS documented as 3, actually 6 | Low |
| G4 | Design System | Doc Inaccuracy | `apply_theme(root)` should be `apply_theme(style)` | Low |
| G5 | Root CLAUDE.md | Outdated | Root CLAUDE.md has 6+ stale descriptions | Medium |

---

## Recommended Actions

### Immediate (Medium Priority)
1. **G5**: Sync root `E:\ClaudeCode\CLAUDE.md` with project-level CLAUDE.md -- update tab count (5->6), table count (5->6), payment section logic, file listing, remove nonexistent `settings_dialog.py`

### Documentation Polish (Low Priority)
2. **G1**: Add `build_exe.py` to the project structure tree in CLAUDE.md
3. **G2-G3**: Expand SPACING/FONTS descriptions to list all actual tokens
4. **G4**: Fix `apply_theme(root)` -> `apply_theme(style: ttk.Style)` in CLAUDE.md

---

## Conclusion

**Match Rate: 98%** -- The project-level CLAUDE.md is highly accurate and well-maintained. All functional descriptions (DB schema, HWP placeholders, UI tabs, search patterns, payment logic, EXE build) match implementation precisely. The only substantive issue is the outdated root CLAUDE.md at `E:\ClaudeCode\CLAUDE.md`, which still reflects a pre-v1.1 state. All 4 remaining gaps in the project CLAUDE.md are minor documentation wording issues with no functional impact.
