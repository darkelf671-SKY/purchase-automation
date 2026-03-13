# Design-Implementation Gap Analysis Report

> **Summary**: Purchase tab UI restructure - design vs implementation comparison
>
> **Author**: gap-detector
> **Created**: 2026-03-12
> **Status**: Approved

---

## Analysis Overview
- **Analysis Target**: purchase-tab-restructure (UI reorganization)
- **Design Document**: `docs/02-design/features/purchase-tab-restructure.design.md`
- **Implementation Path**: `ui/tab_purchase.py`
- **Analysis Date**: 2026-03-12

## Overall Scores

| Category | Score | Status |
|----------|:-----:|:------:|
| Build Order Match | 100% | PASS |
| Section Structure Match | 100% | PASS |
| Widget Migration Match | 100% | PASS |
| Safety Guards Match | 100% | PASS |
| Unchanged Methods Preserved | 100% | PASS |
| **Overall** | **100%** | PASS |

## Requirement-by-Requirement Verification

### Req 1: New `_build_ui()` order

**Design**: banner -> items -> quote -> vendor_payment -> draft -> action buttons

**Implementation** (lines 374-405):
```
_build_edit_banner()           # 0. banner
_build_items_section()         # 1. items
(item_name trace)              # auto-fill title
_build_quote_section()         # 2. quote
_build_vendor_payment_section()# 3. vendor_payment
_build_draft_section()         # 4. draft
(action buttons frame)         # buttons
```

**Result**: MATCH -- order is exactly banner -> items -> quote -> vendor_payment -> draft -> buttons. The item_name trace is placed between items and quote (design shows it after draft, but design line 30-31 says "after items section"), which is functionally correct and matches the intent.

### Req 2: `_build_items_section()` -- LabelFrame title and VAT placement

| Design Spec | Implementation (line) | Match |
|------------|----------------------|:-----:|
| LabelFrame `" 1 ..."` | `" 1 ... "` (line 471) | PASS |
| VAT radios at top | `vat_frame` at top of items_frame (line 475-487) | PASS |
| `_vat_radios` list created here | Lines 478-484 | PASS |
| `_vat_hint_label` created here | Line 485-487 | PASS |
| Separator after VAT | Line 489 | PASS |
| Items table code unchanged | Lines 491-601 (canvas, headers, bottom buttons, totals) | PASS |

**Result**: MATCH

### Req 3: `_build_quote_section()` -- new method replacing survey + quote_compare

| Design Spec | Implementation (line) | Match |
|------------|----------------------|:-----:|
| LabelFrame `" 2 ..."` | `" 2 ... "` (line 605) | PASS |
| Search keyword radios at top | Lines 609-618 | PASS |
| Site buttons below keywords | Lines 620-631 | PASS |
| Separator | Line 632 | PASS |
| Reuse `_build_quote_frame` | Lines 637-638 | PASS |
| Lowest price selection + sole quote | Lines 642-654 | PASS |

**Result**: MATCH

### Req 4: `_build_vendor_payment_section()` -- new method extracted from draft

| Design Spec | Implementation (line) | Match |
|------------|----------------------|:-----:|
| LabelFrame `" 3 ..."` | `" 3 ... "` (line 658) | PASS |
| Vendor combo + new registration | Lines 662-672 | PASS |
| Vendor info LabelFrame | Lines 674-700 | PASS |
| Payment method radios | Lines 702-712 | PASS |
| Bank info LabelFrame (conditional) | Lines 714-737 | PASS |
| `_bank_info_frame` parent = vendor_frame | Line 716: parent is `vendor_frame` | PASS |

**Result**: MATCH

### Req 5: `_build_draft_section()` -- trimmed to rows 0-8

| Design Spec | Implementation (line) | Match |
|------------|----------------------|:-----:|
| LabelFrame `" 4 ..."` | `" 4 ... "` (line 743) | PASS |
| Template row (row 0) | Lines 747-762 | PASS |
| Separator (row 1) | Lines 764-765 | PASS |
| Title (row 2) | Lines 768-774 | PASS |
| Date (row 3) | Lines 777-784 | PASS |
| Department (row 4) | Lines 787-796 | PASS |
| Content (row 5) | Lines 799-805 | PASS |
| Remark (row 6) | Lines 808-811 | PASS |
| Separator (row 7) | Lines 813-814 | PASS |
| Options (row 8) | Lines 816-837 | PASS |
| No vendor/payment rows (9-12) | Confirmed absent from draft_section | PASS |

**Result**: MATCH

### Req 6: `_build_survey_section()` deleted

Grep for `_build_survey_section` and `_build_quote_compare_section` returned zero matches.

**Result**: MATCH

### Req 7: Build order safety guards

| Design Spec | Implementation (line) | Match |
|------------|----------------------|:-----:|
| `_search_field_var` pre-declared in `__init__` | Line 345: `self._search_field_var = tk.StringVar(value="item")` | PASS |
| `_update_kw_preview` has `hasattr` guard for `_kw_preview` | Line 1375: `if hasattr(self, '_kw_preview'):` | PASS |

**Result**: MATCH

### Req 8: Unchanged methods preserved

All methods listed as "no changes required" exist at their expected locations:

| Method | Line | Present |
|--------|------|:-------:|
| `load_purchase()` | 1440 | PASS |
| `_reset_form()` | 1258 | PASS |
| `_validate()` | 1565 | PASS |
| `_generate_documents()` | 1699 | PASS |
| `_build_purchase_data()` | 1649 | PASS |
| `_on_draft_vendor_select()` | 1124 | PASS |
| `_check_total_mode_vat()` | 892 | PASS |

**Result**: MATCH

## Differences Found

### Missing Features (Design present, Implementation absent)
None.

### Added Features (Design absent, Implementation present)
None material. Minor additions that are consistent with design intent (copy mode banner, remainder label) were pre-existing features carried over, not new additions from this restructure.

### Changed Features (Design != Implementation)
None.

## Summary

The implementation is a perfect match to the design document. All 8 requirements are fully satisfied:

1. Build order matches exactly (banner -> items -> quote -> vendor_payment -> draft -> buttons)
2. VAT controls moved into `_build_items_section()` with correct LabelFrame title
3. `_build_quote_section()` consolidates search keywords, site buttons, quote frames, and selection
4. `_build_vendor_payment_section()` correctly extracts vendor/payment from draft section
5. `_build_draft_section()` trimmed to rows 0-8 only
6. `_build_survey_section()` and `_build_quote_compare_section()` are fully deleted
7. Safety guards (`_search_field_var` in `__init__`, `hasattr` on `_kw_preview`) are in place
8. All 7 specified unchanged methods remain present and unmodified in structure

**Match Rate: 100%**
