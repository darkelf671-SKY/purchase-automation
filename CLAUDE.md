# 물품구매 자동화 시스템 — Claude 작업 컨텍스트

## 프로젝트 개요
공공기관 방식의 물품 비교견적 2개 수집 후 기안서/산출기초조사서를 HWP 양식에 자동 생성하는 데스크톱 앱.

- **프로그램명**: 구매기안 자동화 시스템 v1.0
- **제작**: 전산팀 장길섭
- **언어**: Python 3
- **UI**: tkinter (6탭 구성 — 구매 조사 / 검수 입력 / 이력 조회 / 업체 관리 / 수의계약 사유 / 기안 템플릿)
- **HWP 자동화**: win32com (HWPFrame.HwpObject)
- **Excel**: openpyxl
- **DB**: SQLite3
- **시장조사**: 반자동화(webbrowser 브라우저 열기 + 직접 입력)

## 프로젝트 구조
```
purchase-automation/
├── main.py                        # 진입점
├── config.py                      # API키, 경로, 사이트 URL, 제외키워드
├── core/
│   ├── models.py                  # PurchaseData, VendorQuote, PurchaseItem, InspectionData
│   ├── naver_api.py               # 네이버 쇼핑 검색 API (NaverShoppingAPI)
│   ├── filter_engine.py           # 검색 결과 필터링 (FilterEngine)
│   ├── screenshot.py              # 화면 캡처 (전체/구역/파일선택+PDF)
│   └── semi_auto.py               # 반자동화 (SemiAutoHelper, 브라우저 오픈)
├── db/
│   ├── database.py                # DB 초기화·마이그레이션 (6개 테이블)
│   ├── purchase_repo.py           # 구매 CRUD
│   ├── inspection_repo.py         # 검수 CRUD
│   ├── vendor_repo.py             # 업체 CRUD
│   ├── sole_contract_repo.py      # 수의계약 사유 CRUD
│   └── draft_template_repo.py     # 기안 템플릿 CRUD
├── documents/
│   ├── hwp_generator.py           # HWP 문서 생성 (HwpGenerator)
│   ├── excel_generator.py         # Excel 문서 생성 (ExcelGenerator)
│   └── templates/                 # HWP/Excel 양식 파일 위치
│       ├── 산출기초조사서.hwp      # 완성됨
│       ├── 내부기안.hwp           # 미완성 (사용자 직접 자리표시자 삽입)
│       └── 물품검수조서.hwp       # 미완성 (사용자 직접 자리표시자 삽입)
├── ui/
│   ├── app.py                     # 메인 윈도우 (Notebook 6탭, 설정 Hot Reload)
│   ├── base_dialog.py             # 다이얼로그 공통 베이스 클래스 (BaseDialog)
│   ├── design_system.py           # 디자인 시스템 (COLORS, SPACING, FONTS, apply_theme)
│   ├── tab_purchase.py            # 탭1: 구매 조사 (견적입력+기안서 생성+템플릿 저장)
│   ├── tab_inspection.py          # 탭2: 검수 입력 (설정 Hot Reload 지원)
│   ├── tab_history.py             # 탭3: 이력 조회
│   ├── tab_vendor.py              # 탭4: 업체 관리
│   ├── tab_sole_contract.py       # 탭5: 수의계약 사유 관리
│   ├── tab_draft_template.py      # 탭6: 기안 템플릿 관리
│   └── dialog_settings.py         # 설정 다이얼로그 (폴더+부서+검수자+입회자+Hot Reload)
└── data/
    ├── purchase.db                # SQLite DB
    ├── outputs/                   # 생성된 문서 저장
    └── screenshots/               # 캡처 이미지 저장
```

## 핵심 설계 결정사항

### HWP 자리표시자 방식
- 템플릿 HWP 파일에 `{{PLACEHOLDER}}` 삽입
- `hwp_generator.py`에서 `AllReplace` 액션으로 일괄 치환
- **중요**: `FindReplace` 액션이 아닌 `AllReplace` 액션을 사용해야 함
  ```python
  hwp.HAction.GetDefault("AllReplace", hwp.HParameterSet.HFindReplace.HSet)
  hwp.HParameterSet.HFindReplace.FindString = placeholder
  hwp.HParameterSet.HFindReplace.ReplaceString = str(value)
  hwp.HParameterSet.HFindReplace.IgnoreMessage = 1
  hwp.HAction.Execute("AllReplace", hwp.HParameterSet.HFindReplace.HSet)
  ```
- 양식 레이아웃 변경 시 HWP 파일만 수정, 코드 수정 불필요
- 새 자리표시자 추가 시에만 `hwp_generator.py`의 `replacements` 딕셔너리 수정

### 견적 정렬 규칙
- **문서 출력 시 항상 견적1 = 최저가, 견적2 = 비교 업체**
- 사용자가 어느 견적을 선택하든 자동 정렬
- `generate_calculation()` 에서 `low/high` 변수로 처리:
  ```python
  low  = data.selected  # 최저가
  high = data.vendor2 if data.selected_vendor == 1 else data.vendor1  # 비교
  ```

### 한글 금액 표기 형식
- 공식 문서 표기: `一金일금삼백이십오만칠천구백팔십원(₩3,257,980)`
- `_format_korean_amount()` 함수 사용
- 십/백/천/만 앞 '일' 유지 (일십, 일백, 일천, 일만, 일십만 등)

### 날짜 형식
- `{{TODAY}}` = `2026. 03. 06` 형식 (`%Y. %m. %d`)

### 산출기초조사서 자리표시자
| 자리표시자 | 내용 |
|-----------|------|
| `{{ITEM_NAME}}` | 품명 |
| `{{SPEC}}` | 규격/사양 |
| `{{UNIT}}` | 단위 |
| `{{QUANTITY}}` | 수량 |
| `{{TOTAL_PRICE_FORMAL}}` | 최저가 공식표기 (문서 상단) |
| `{{VENDOR1_NAME}}` | 견적1 업체명 (최저가) |
| `{{VENDOR1_TOTAL}}` | 견적1 총가격 |
| `{{VENDOR2_NAME}}` | 견적2 업체명 (비교) |
| `{{VENDOR2_TOTAL}}` | 견적2 총가격 |
| `{{SEL_VENDOR}}` | 산출가격 업체명 (최저가) |
| `{{SEL_TOTAL}}` | 산출가격 (최저가) |
| `{{TODAY}}` | 작성일 |

### 기안서 자리표시자 (템플릿: 내부기안.hwp)
| 자리표시자 | 내용 |
|-----------|------|
| `{{DRAFT_TITLE}}` | 제목 |
| `{{DRAFT_CONTENT}}` | 내용 |
| `{{ITEM_NAME}}` | 품명 |
| `{{SPEC}}` | 규격 |
| `{{QTY_WITH_UNIT}}` | 수량+단위 (예: 2대) |
| `{{UNIT_PRICE}}` | 단가 (숫자, 천단위 쉼표) |
| `{{TOTAL_PRICE}}` | 총금액 (숫자) |
| `{{REMARK}}` | 비고 |
| `{{PURCHASE_AMOUNT}}` | 구매금액 한글 (예: 일금팔십만원정(\800,000)-VAT포함) |
| `{{VENDOR_NAME}}` | 상호 |
| `{{VENDOR_CEO}}` | 대표자 |
| `{{VENDOR_BIZ_NO}}` | 사업자등록번호 |
| `{{VENDOR_ADDRESS}}` | 주소 |
| `{{PAYMENT_METHOD}}` | 계약방법 (수의계약 고정) |
| `{{PAYMENT_SECTION}}` | 계약방법 조건부 섹션 ("계약방법 : 수의계약", 동적 순번) |
| `{{SOLE_SECTION}}` | 수의계약 사유 조건부 섹션 |
| `{{ATTACHMENTS}}` | 첨부파일 목록 |
| `{{DEPARTMENT}}` | 부서명 |
| `{{GRAND_TOTAL_FORMAL}}` | 전체 합계 한글 금액 표기 |
| `{{TODAY}}` | 작성일 (2026. 03. 06 형식) |

### 물품검수조서 자리표시자
| 자리표시자 | 내용 |
|-----------|------|
| `{{ITEM_NAME}}` | 품목 (품명) |
| `{{VENDOR_NAME}}` | 납품자 (결정 업체명) |
| `{{CONTRACT_AMOUNT}}` | 계약금액 — `일금...원(\N,NNN원)` 형식 |
| `{{CONTRACT_DATE}}` | 계약체결년월일 — 기안날짜 `2026년 01월 05일` 형식 |
| `{{DELIVERY_DEADLINE}}` | 납품기한 — 기안날짜 |
| `{{DELIVERY_DATE}}` | 납품일 — 검수날짜 |
| `{{INSPECTION_DATE}}` | 검수년월일 — 검수날짜 |
| `{{INSPECTION_QTY}}` | 검수량 — `품명(규격)` 또는 `품명(규격) x N개` |
| `{{INSPECTOR}}` | 검수자 |
| `{{WITNESS}}` | 입회자 (없으면 `-`) |

### 날짜 형식
- `{{TODAY}}` (산출기초조사서용) = `2026. 03. 06` 형식 (`%Y. %m. %d`)
- `{{CONTRACT_DATE}}` 등 (물품검수조서용) = `2026년 01월 05일` 형식 (`%Y년 %m월 %d일`)

## 다중 품목 (1:N) 구조 — v1.1

### 데이터 구조
- `purchase_items` 테이블: `purchases` 1건에 N개 품목 (ON DELETE CASCADE)
- `PurchaseItem` 모델: seq, item_name, spec, unit, quantity, unit_price, total_price
- `PurchaseData.items`: list[PurchaseItem] — `item_name`, `spec`, `quantity` 등은 첫 품목 프로퍼티로 하위 호환 유지
- `PurchaseData.grand_total`: 전체 품목 금액 합산

### 견적 구조 변경
- 견적1 `total_price` = 품목 합산 자동 (UI에서 readonly)
- 견적2: 품목별 `v2_unit_price` 입력 → `v2_total_price` 자동 계산
- `PurchaseData.vat_mode`: `"inclusive"` (입력가=VAT포함) | `"exclusive"` (입력가×1.1)

### PurchaseItem 추가 필드
- `v2_unit_price: int` — 견적2(비교업체) 품목별 단가
- `remark: str` — 품목별 비고

### HWP 다중 품목 방식 (산출기초조사서, 내부기안)
- 템플릿에 `{{SEQ_01}}`~`{{SEQ_15}}`, `{{ITEM_01}}`~`{{ITEM_15}}` 등 15행 인덱스 자리표시자 필요
- N개 품목 채우고 나머지 AllReplace("") → `{{GRAND_TOTAL}}` 기준 빈 행 삭제
- `MAX_ITEM_ROWS = 15` (config 아닌 hwp_generator.py에 정의)

### 물품검수조서 다중 품목
- 테이블 없이 `{{INSPECTION_QTY}}`에 줄바꿈(\r\n) 나열
- 템플릿 수정 불필요

### 물품검수내역서(Excel) 다중 품목
- `ITEM_START_ROW = 4`에서 시작, `n > 1`이면 `insert_rows()` 삽입
- 템플릿 수정 불필요

## 미결 이슈 (추후 수정)
- [x] **S2B(학교장터)** — EUC-KR 인코딩 검색 URL 적용 완료
- [ ] **내부기안.hwp 템플릿** — 자리표시자 삽입 필요 (사용자 직접 HWP 파일 편집)
- [ ] **물품검수조서.hwp 템플릿** — 자리표시자 삽입 필요 (사용자 직접 HWP 파일 편집)

### 템플릿 파일 수정 필요 (사용자 직접)
- `산출기초조사서.hwp`: 품목 테이블 1행 → 15행, `{{SEQ_01}}`~`{{AMOUNT_15}}` 자리표시자
- `내부기안.hwp`: 동일
- `{{GRAND_TOTAL}}` 자리표시자를 합계 행 금액 셀에 추가 (빈 행 삭제 앵커로 사용)

## 현재 진행 상태
- [x] 프로젝트 구조 설계 및 생성
- [x] DB 스키마 (purchases, inspections, vendors, sole_contract_reasons, purchase_items, draft_templates)
- [x] 데이터 모델 (PurchaseData, VendorQuote, InspectionData) + department 필드
- [x] HWP 생성기 (기안서, 산출기초조사서, 물품검수조서)
- [x] Excel 생성기 (물품검수내역서)
- [x] 탭1: 구매 조사 (수동+자동 통합, 검색키워드 선택, Combobox 구매처명, 캡처 3종)
- [x] 탭2: 검수 입력 (검색 기능, 검수기록 삭제 시 파일도 함께 삭제)
- [x] 탭3: 이력 조회 (검색 기능, 상세 패널, 문서 열기 버튼 6종, 폴더 열기)
- [x] 탭4: 업체 관리 (검색 기능)
- [x] 기안서 다이얼로그 (신규 업체 등록, 구매처 자동 연동)
- [x] 다중 품목 1:N 구조 전환 (purchase_items 테이블, PurchaseItem 모델, 동적 UI, 문서 엔진)
- [x] 설정 다이얼로그 (산출 폴더 경로 지정)
- [x] 화면 캡처 3종 (전체/구역/파일선택+PDF)
- [x] 스크린샷 영구 보관 (SCREENSHOT_DIR 유지 + output_dir 복사)
- [x] 산출기초조사서 생성 후 폼 자동 초기화 + 수동 초기화 버튼
- [x] 디자인 시스템 (COLORS, SPACING, FONTS, apply_theme, 워터마크)
- [x] BaseDialog 패턴 (모든 다이얼로그 공통 베이스)
- [x] 탭6: 기안 템플릿 관리 (검색, 추가/수정/삭제, 툴팁)
- [x] 기안폼→템플릿 저장 (역치환 {{품명}}, 중복 검사, 덮어쓰기)
- [x] 견적1/견적2 합계 구분 표시 (최저가 색상 강조, 수의계약 시 숨김)
- [x] 설정 Hot Reload (부서명/검수자/입회자 즉시 반영)
- [x] 화면 캡처 DPI 스케일링 대응 (물리/논리 좌표 변환, 워터마크 우측 상단)
- [x] 견적 URL 열기 버튼 (webbrowser.open)
- [x] 계약방법 변경 (구매방법 카드/계좌 분기 → "계약방법 : 수의계약" 고정)
- [x] HWP COM 안정화 (Dispatch + CoInitialize, gen_py 캐시 리디렉션)
- [x] EXE 단일 파일 빌드 (PyInstaller --onefile, 시드 DB 포함)
- [x] 검수입력/이력조회 검색 UI 통일 (체크박스: 품명/부서명/기안제목/기안내용)
- [x] 검수입력 기안정보 표시 (기안제목/기안내용/비고, 이력조회 상세 패널 스타일 통일)
- [x] 구매건 수정 모드 (이력→불러오기→수정→재생성, DB UPDATE, 기존 폴더 덮어쓰기)
- [x] 검수 완료 건 수정 시 경고 + 검수 자동 삭제 연동
- [x] 총액 입력 모드 (할인가 역산: 총액→단가 자동 계산, VAT 자동 비활성화)
- [ ] 내부기안.hwp 자리표시자 삽입 (사용자 작업)
- [ ] 물품검수조서.hwp 자리표시자 삽입 (사용자 작업)
- [ ] 전체 통합 테스트

## draft_templates 테이블
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 자동 증가 |
| label | TEXT NOT NULL | 별칭 (고유 식별용) |
| title | TEXT | 기안제목 |
| content | TEXT NOT NULL | 기안내용 (`{{품명}}` 치환자 포함 가능) |
| remark | TEXT | 비고 |
| created_at | TIMESTAMP | 등록일시 |

## purchases 테이블 추가 컬럼 (미문서화 항목)
| 컬럼 | 설명 |
|------|------|
| draft_date | 기안일자 |
| doc_folder | 문서 저장 폴더 경로 |
| vat_mode | VAT 모드 (inclusive/exclusive) |
| item_count | 품목 수 |
| doc_draft_remark | 기안서 비고 |

## 디자인 시스템 (design_system.py)
- `COLORS`: primary, success, warning, danger, total, border, tooltip 등 색상 상수
- `SPACING`: sm/md/lg 간격 상수
- `FONTS`: heading/body/small 폰트 상수
- `apply_theme(root)`: ttk 스타일 일괄 적용 (Primary/Danger 버튼, Treeview 행 교대색)
- `configure_treeview_tags(tree)`: 행 교대색 태그 설정
- `insert_with_alternating(tree, ...)`: 교대색 자동 적용 삽입

## BaseDialog 패턴 (base_dialog.py)
- 모든 다이얼로그의 공통 베이스 (`OutputSettingsDialog`, `DraftTemplateDialog`, `SaveAsTemplateDialog`, `VendorDialog`, `SoleContractDialog` 등)
- `_build_content(f)`: 서브클래스에서 오버라이드
- `_on_save()`: 서브클래스에서 오버라이드
- `_fire_save_callback()`: 저장 콜백 실행

## 설정 Hot Reload 패턴
1. `dialog_settings.py` → 저장 시 `on_save_callback()` 호출
2. `app.py._on_settings_saved()` → 각 탭의 refresh 메서드 호출
3. `tab_inspection.reload_settings()` → 빈 필드만 설정값으로 갱신 (사용자 입력 보존)

## 화면 캡처 (screenshot.py)
- DPI 인식: `main.py` 최상단에서 `SetProcessDpiAwareness(1)` 설정 (tkinter 생성 전 필수)
- 전체캡처: 메인 윈도우 `withdraw()` → `grab_clean_screen()` → 워터마크 → 저장 → `deiconify()`
- 구역캡처: 메인 윈도우 `withdraw()` → `grab_clean_screen()` → 사전 캡처 이미지를 `capture_region(full_img)` 에 전달 → 오버레이는 논리 해상도(`winfo_screenwidth`), 크롭은 `scale_x/y`로 물리 좌표 변환
- 워터마크: 우측 상단, 이미지 폭이 좁으면 좌측 정렬 폴백

## EXE 빌드 (build_exe.py)
- `python build_exe.py` → PyInstaller `--onefile --windowed`
- 시드 DB: 현재 DB에서 업체/수의계약/기안템플릿만 추출 → `seed.db` → EXE 내장
- 첫 실행 시 `config.py`에서 `seed.db` → `purchase.db` 자동 복사
- HWP 템플릿: `_MEIPASS` (읽기전용), DB/출력물: EXE 옆 `data/` (쓰기)
- HWP COM: `Dispatch` (late binding) + `CoInitialize/CoUninitialize` + gen_py 캐시 TEMP 리디렉션

## 계약방법 ({{PAYMENT_SECTION}})
- 포함 시: `"{num}. 계약방법 : 수의계약"` (고정 텍스트, 동적 순번)
- 미포함 시: 해당 단락 삭제 (`delete_paragraphs`)
- 기존 카드/계좌이체 분기 로직 제거됨

## 주요 UI 패턴 및 주의사항

### tkinter pack 순서 규칙
- `btn_frame.pack(side="bottom")` → Treeview보다 **먼저** pack 해야 버튼이 보임
- 순서: 버튼 프레임 → 스크롤바 → Treeview

### 검색 기능 구현 패턴 (5개 탭 공통)
```python
self._search_var = tk.StringVar()
self._search_var.trace_add("write", lambda *_: self._apply_filter())
# refresh() → self._records 갱신 후 _apply_filter() 호출
# _apply_filter() → _search_var 기준으로 Treeview 재구성
```
- 검수입력/이력조회: 체크박스 방식 (☑품명 ☑부서명 ☑기안제목 ☑기안내용)
- `_chkvar()` 헬퍼로 체크박스 생성 + `_apply_filter` 바인딩
- 검색 대상: `item_name`, `department`, `doc_draft_title`, `doc_draft_content`

### 검수입력 기안정보 표시
- 구매건 선택 시 상단에 기안제목/기안내용/비고 표시 (읽기 전용)
- 이력조회 상세 패널과 동일한 레이아웃 (라벨 width=8, anchor="e")
- 기안내용 200자 초과 시 말줄임(`...`) 처리, wraplength=600

### 구매처 자동 연동 흐름
1. `tab_purchase.py` - Combobox `<<ComboboxSelected>>` 이벤트 → `self._vendor_records[slot]` 저장
2. `_generate_documents()` → `preselect_vendor = self._vendor_records[sel-1]` 추출
3. `DraftDialog(preselect_vendor=...)` → 업체 Combobox 자동 선택 + 정보 자동 채움
4. 폴백: 이름 strip 비교 → 그래도 없으면 수동 선택 / 신규 등록

### 검수 기록 삭제 (`_delete_inspection`)
- 삭제 전 경고: 삭제될 파일명 목록 명시 (물품검수내역서, 물품검수조서)
- 파일 삭제 → DB 삭제 순서
- 이력 조회는 refresh() 시 _insp_map 재구성으로 자동 반영

### 재검수 연결
- `_generate_documents()` → `inspection_repo.insert()` 새 id 생성 → `update_docs()` 새 파일 경로 저장
- `select_all_grouped()`: `MAX(id) GROUP BY purchase_id`로 최신 검수 1건만 조회

## 구매건 수정 모드 (v1.2)

### 상태 변수
- `_editing_purchase_id: int | None` — None=신규, int=수정 모드
- `_editing_doc_folder: str | None` — 기존 폴더 경로

### 동작 흐름
1. 이력 조회 → "구매탭에 불러오기" → `load_purchase()` → 수정 모드 활성화
2. 수정 모드 배너 표시 (노란색 + "수정 취소" 버튼)
3. "재생성" 클릭 → `_regenerate_documents()`:
   - 검수 기록 확인 → 경고 + 자동 삭제 [D3]
   - 기존 폴더에 문서 덮어쓰기 [D4 폴더명 유지]
   - `repo.update()` + `repo.update_items()` (DB UPDATE)
4. "수정 취소" → 폼 초기화 + 신규 모드 복귀

### purchase_repo 추가 함수
- `update(purchase_id, data)`: purchases 테이블 UPDATE
- `update_items(purchase_id, items)`: DELETE + re-INSERT (CASCADE 활용)

## 총액 입력 모드 (v1.2)

### 개요
인터넷 할인가로 구매 시 총액÷수량 나머지 발생 대응. 총액 입력 → 단가 자동 역산.

### PurchaseItem.price_input_mode
- `"unit"` (기본): 단가 입력 → 합계 자동 계산
- `"total"`: 총액 입력 → 단가 역산 (`total // quantity`)

### VAT 자동 비활성화 [D1]
- 총액 모드 활성화 시 VAT → `inclusive` 강제, 라디오버튼 disabled
- 총액 모드 해제 시 VAT 라디오버튼 복원

### ItemRow 양방향 계산
- `_recalc()`: 단가 → 합계 (기존, 총액 모드에서는 무시)
- `_recalc_reverse()`: 합계 → 단가 역산 (총액 모드 전용)
- `_updating` 플래그: 재진입 방지

## 실행 방법
```bash
cd E:\ClaudeCode\purchase-automation
python main.py
```

## 의존성
```
pywin32       # HWP COM 자동화
openpyxl      # Excel 생성
requests      # 네이버 API
Pillow        # 스크린샷
pyautogui     # 화면 캡처
```
