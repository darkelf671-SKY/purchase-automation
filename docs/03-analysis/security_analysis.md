# 보안 취약점 분석 보고서

**프로젝트**: 구매기안 자동화 시스템 v1.0
**분석일**: 2026-03-12
**분석 대상**: 전체 소스코드 (Python 3 / tkinter / SQLite3 / win32com)
**위협 모델**: 로컬 데스크톱 앱 (네트워크 서버 아님)

---

## 요약

| 심각도 | 건수 | 설명 |
|--------|------|------|
| Critical | 0 | - |
| High | 2 | API 키 평문 저장, 폴더 삭제 경로 미검증 |
| Medium | 4 | Path Traversal 가능성, COM 보안 우회, 에러 정보 노출, 설정 파일 무결성 |
| Low | 4 | 입력값 정수 파싱 미검증, URL 스킴 검증 부족, 임시파일 경합, DB 암호화 미적용 |

**총 점수: 78/100** (로컬 데스크톱 앱 기준)

> 본 애플리케이션은 **로컬 전용 데스크톱 앱**으로 네트워크 공격 표면이 극히 제한적입니다.
> 아래 분석은 OWASP Top 10을 기준으로 하되, 데스크톱 앱 특성을 반영하여 실제 위험도를 조정했습니다.

---

## 1. SQL Injection (A03: Injection)

### 판정: 안전 (Pass)

모든 DB 레이어에서 **파라미터 바인딩(Parameterized Query)**을 일관되게 사용하고 있습니다.

**검증 파일 및 패턴:**

| 파일 | 패턴 | 결과 |
|------|------|------|
| `db/purchase_repo.py` | Named params (`:purpose`, `:item_name`) + positional (`?`) | 안전 |
| `db/inspection_repo.py` | Positional params (`?`) | 안전 |
| `db/vendor_repo.py` | Named params (`:name`, `:ceo`) | 안전 |
| `db/sole_contract_repo.py` | Positional params | 안전 |
| `db/draft_template_repo.py` | Positional params | 안전 |
| `db/database.py` | DDL(`CREATE TABLE`) + 마이그레이션 ALTER | 안전 (사용자 입력 없음) |

**양호 사례** (`purchase_repo.py:43`):
```python
cur = conn.execute(sql, params)  # Named parameter binding
```

**양호 사례** (`vendor_repo.py:12`):
```python
cur = conn.execute(sql, data)  # Dict-based parameter binding
```

문자열 포매팅(f-string, .format())으로 SQL을 구성하는 코드는 발견되지 않았습니다.

---

## 2. API 키 관리 (A02: Cryptographic Failures)

### 판정: High - 평문 저장

**위치**: `config.py:153-155`

```python
_s = load_settings()
NAVER_CLIENT_ID     = _s.get("naver_client_id")     or os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = _s.get("naver_client_secret") or os.environ.get("NAVER_CLIENT_SECRET", "")
```

**문제점:**
- 네이버 API 키가 `data/settings.json`에 **평문 JSON**으로 저장됨
- `settings.json`은 EXE 옆 `data/` 폴더에 위치하여 누구나 열람 가능
- 환경변수 폴백이 있으나, 실제 운용 시 JSON 저장이 주 경로

**위험도 조정:** 로컬 데스크톱 앱이므로 파일 시스템 접근 권한은 OS 사용자 수준으로 제한됨. 다만 공유 PC 환경(공공기관)에서는 다른 사용자가 열람할 수 있어 **High**로 유지합니다.

**권장 조치:**
1. Windows Credential Manager(`keyring` 라이브러리) 사용으로 시스템 자격 증명 저장소 활용
2. 또는 Windows DPAPI(`win32crypt.CryptProtectData`)로 암호화 후 저장
3. 최소한 `settings.json`에 대한 파일 권한 제한 (ACL 설정)

---

## 3. 파일 경로 조작 (A01: Broken Access Control / Path Traversal)

### 3-1. 출력 폴더 경로 생성 — 부분적 방어

**위치**: `config.py:80-98`

```python
def make_output_dir(item_name: str) -> Path:
    safe_name = item_name.replace("/", "_").replace("\\", "_").strip()
    folder = base / f"{datetime.now().strftime('%Y%m%d')}_{safe_name}"
    ...

def make_output_dir_named(folder_name: str) -> Path:
    safe = folder_name.replace("/", "_").replace("\\", "_").replace(":", "_").strip()
    folder = base / safe
```

**양호 사항:** `/`, `\`, `:` 문자를 `_`로 치환하여 기본적인 Path Traversal 방어가 존재합니다.

**잔여 위험 (Medium):**
- `..` 문자열에 대한 명시적 검증이 없음 (예: `item_name = ".."`이면 `base/20260312_..`이 생성되나, 이는 실제 상위 디렉토리 탈출이 아님 -- `..`은 디렉토리 이름 자체가 됨)
- 그러나 `get_output_dir()` 자체가 사용자가 설정한 임의 경로를 사용하므로, 설정값이 조작되면 의도하지 않은 위치에 파일이 생성될 수 있음

**권장 조치:**
```python
def make_output_dir_named(folder_name: str) -> Path:
    safe = folder_name.replace("/", "_").replace("\\", "_").replace(":", "_").strip()
    safe = safe.replace("..", "_")  # 추가 방어
    folder = base / safe
    # 최종 경로가 base 하위인지 검증
    if not str(folder.resolve()).startswith(str(base.resolve())):
        raise ValueError("잘못된 폴더 이름입니다.")
```

### 3-2. HWP 출력 파일명 생성

**위치**: `hwp_generator.py:501-502`

```python
safe_title = title.replace("/", "_").replace("\\", "_").replace(":", "_").strip()
filename = f"{safe_title}.hwp"
```

동일한 패턴으로 기본 방어가 적용되어 있으나, `..` 검증 누락.

### 3-3. 폴더 삭제 시 경로 검증 부재 — High

**위치**: `ui/tab_history.py:390-392`

```python
if folder_exists:
    if not self._delete_folder_with_retry(folder):
        return
```

`_delete_folder_with_retry()` (`tab_history.py:402-430`)에서 `shutil.rmtree(path)`를 호출하는데, `folder` 값은 DB에서 읽어온 `doc_folder` 컬럼값을 그대로 사용합니다.

**문제점:**
- DB의 `doc_folder` 값이 변조되었거나 의도치 않은 경로를 가리킬 경우 **임의 디렉토리 삭제** 가능
- `shutil.rmtree()`는 재귀적으로 하위 전체를 삭제하므로 피해 범위가 큼
- 현재 코드에는 삭제 대상 경로가 출력 디렉토리 하위인지 확인하는 로직이 없음

**권장 조치:**
```python
def _delete_folder_with_retry(self, folder_path: str) -> bool:
    path = Path(folder_path).resolve()
    allowed_base = Path(get_output_dir()).resolve()
    # 출력 디렉토리 하위인지 검증
    if not str(path).startswith(str(allowed_base)):
        messagebox.showerror("보안 오류",
            f"삭제 대상이 출력 폴더 외부에 있어 삭제할 수 없습니다.\n{path}")
        return False
    # ... 기존 로직
```

### 3-4. 파일 열기 — os.startfile

**위치**: `ui/tab_history.py:331, 358, 369`

```python
os.startfile(path)
```

`os.startfile()`은 Windows 셸에 파일 열기를 위임하므로, 확장자 기반 프로그램 연결을 통해 실행됩니다. DB에 저장된 경로를 그대로 사용하므로 DB 변조 시 의도치 않은 파일 실행이 가능하지만, 로컬 앱에서 DB는 사용자 본인이 관리하므로 Low 수준입니다.

---

## 4. 사용자 입력 검증 (A03: Injection / A04: Insecure Design)

### 4-1. 숫자 입력 필드 — 적절한 예외 처리

**위치**: `ui/tab_purchase.py` (ItemRow 클래스)

```python
try:
    price = int(self.price_var.get().replace(",", ""))
except (ValueError, tk.TclError):
    self.total_var.set("0")
```

모든 숫자 파싱 지점에서 `try/except`로 처리하고 있어 기본적인 방어가 됩니다.

**잔여 위험 (Low):**
- 음수 입력에 대한 명시적 검증 없음 (음수 금액이 DB에 저장될 수 있음)
- 매우 큰 숫자 입력 시 정수 오버플로우는 Python에서 발생하지 않으나, HWP 치환 시 레이아웃이 깨질 수 있음

### 4-2. 텍스트 입력 — 미sanitize

기안제목, 기안내용, 비고, 품명, 규격 등 텍스트 필드에 대한 별도 sanitization이 없습니다. 그러나:
- SQL은 파라미터 바인딩으로 안전
- HWP 치환 시 `_allreplace()`에서 제어문자를 제거 (`hwp_generator.py:236-237`)
- 웹 출력이 아니므로 XSS 위험 없음

```python
# hwp_generator.py:236-237 — 제어문자 제거
clean = str(replace).replace("\r\n", "\n").replace("\r", "\n")
clean = "".join(c for c in clean if c in ("\t", "\n") or (ord(c) >= 32))
```

이 부분은 **양호**합니다.

---

## 5. COM 자동화 보안 (A05: Security Misconfiguration)

### 5-1. HWP 보안 모듈 우회 — Medium

**위치**: `hwp_generator.py:158-187`

```python
def _open_hwp(self):
    pythoncom.CoInitialize()
    hwp = win32com.client.Dispatch("HWPFrame.HwpObject")
    # 보안 모듈 등록 시도
    for module_name in ("FilePathCheckerModuleExample", "AutomationModule"):
        try:
            hwp.RegisterModule("FilePathCheckDLL", module_name)
            ...
    # 레지스트리 기반 보안 해제 시도
    try:
        import winreg
        key_path = r"SOFTWARE\HNC\HwpAutomation\Modules"
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        winreg.SetValueEx(key, "FilePathCheckerModule", 0,
                         winreg.REG_SZ, "FilePathCheckerModuleExample")
```

**문제점:**
- 한/글의 파일 경로 검사 보안 모듈을 명시적으로 우회하고 있음
- 레지스트리 값을 직접 수정하여 보안 설정을 변경함
- 이는 한/글 자동화의 일반적인 패턴이지만, 보안 관점에서는 위험 요소

**위험도 조정:** 한/글 COM 자동화의 공식적/비공식적 표준 패턴이며, 로컬에서 신뢰할 수 있는 템플릿만 사용하므로 실제 위험은 제한적입니다. 다만 레지스트리 변경은 시스템 전체에 영향을 미치므로 Medium으로 분류합니다.

**권장 조치:**
- 레지스트리 변경 전 기존 값 백업 및 앱 종료 시 복원
- 또는 레지스트리 변경 없이 `RegisterModule`만 사용하도록 제한

### 5-2. COM 에러 처리 — 양호

```python
def _close_and_quit(self, hwp):
    try:
        hwp.Clear(1)
    except Exception:
        pass
    try:
        hwp.Quit()
    except Exception:
        pass
    try:
        pythoncom.CoUninitialize()
    except Exception:
        pass
```

COM 객체의 생명주기 관리에서 예외를 포착하고 있어 리소스 누수 방지가 적절합니다.

### 5-3. 임시파일 처리

**위치**: `hwp_generator.py:470-489`

```python
def _copy_template_to_tmp(self, template_name: str) -> str:
    fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="hwp_", dir=tmp_dir)
    os.close(fd)
    shutil.copy2(str(src), tmp_path)
    return tmp_path

def _remove_tmp(self, tmp_path: str):
    try:
        os.unlink(tmp_path)
    except Exception:
        pass
```

**잔여 위험 (Low):**
- `_remove_tmp` 실패 시 TEMP 디렉토리에 HWP 임시파일이 남을 수 있음
- 민감한 문서 내용이 포함된 임시파일이 정리되지 않을 가능성

---

## 6. 에러 처리 및 정보 노출 (A09: Security Logging and Monitoring Failures)

### 6-1. 예외 메시지 사용자 노출 — Medium

**위치**: `ui/tab_history.py:429`

```python
except Exception as e:
    messagebox.showwarning("폴더 삭제 실패", f"오류:\n{e}", parent=self)
```

**문제점:** 예외 객체의 문자열 표현을 그대로 사용자에게 보여줌. 파일 시스템 경로, 내부 상태 등이 노출될 수 있음.

**유사 패턴 다수 존재:**
- `tab_purchase.py`의 문서 생성 실패 시 예외 메시지 표시
- `hwp_generator.py`의 COM 오류 메시지

**권장 조치:**
- 사용자에게는 일반적인 오류 메시지만 표시
- 상세 예외는 로그 파일에 기록

### 6-2. 로깅 시스템 부재

프로젝트 전체에 `logging` 모듈 사용이 없습니다. 모든 오류가 `messagebox`로만 표시되며, 파일 기반 로그가 없어 사후 분석이 불가능합니다.

**권장 조치:**
```python
import logging
logging.basicConfig(
    filename=str(DATA_DIR / "app.log"),
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
```

---

## 7. 설정 파일 무결성 (A08: Software and Data Integrity Failures)

### 판정: Medium

**위치**: `config.py:104-116`

```python
def load_settings() -> dict:
    if _SETTINGS_PATH.exists():
        try:
            return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_settings(data: dict) -> None:
    _SETTINGS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
```

**문제점:**
- `settings.json`은 평문 JSON으로 누구나 편집 가능
- JSON 파싱 실패 시 빈 딕셔너리를 반환하여 모든 설정이 초기화됨 (데이터 손실)
- 파일 쓰기 중 크래시 시 파일이 손상될 수 있음 (atomic write 미적용)
- `output_dir` 설정값이 조작되면 임의 경로에 파일 생성 가능

**권장 조치:**
- Atomic write (임시파일 쓰기 + rename)
- 설정 파일 변경 시 백업 생성
- `output_dir` 경로 유효성 검증 강화

---

## 8. URL 처리 (A10: SSRF 관련)

### 8-1. URL 스킴 검증 부족 — Low

**위치**: `ui/tab_purchase.py:975-982`

```python
def open_url(uvar=url_var, s=slot):
    u = uvar.get().strip()
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    webbrowser.open(u)
```

**양호 사항:** `http://`, `https://` 접두사가 없으면 자동으로 `https://`를 붙여줍니다.

**잔여 위험 (Low):**
- `file://`, `javascript:` 등 위험한 스킴은 `https://`가 앞에 붙으므로 실행되지 않음
- 이미 `http://` 또는 `https://`로 시작하는 경우에만 그대로 전달되므로 안전

**위치**: `ui/tab_history.py:177-180`

```python
def _open():
    u = uv.get().strip()
    if u:
        webbrowser.open(u)
```

이력 조회 탭에서는 스킴 검증 없이 DB 저장값을 그대로 `webbrowser.open()`에 전달합니다. DB 값이 `file:///C:/...` 같은 값이면 로컬 파일이 열릴 수 있으나, 이는 로컬 앱 특성상 Low 위험입니다.

### 8-2. 검색 URL 생성

**위치**: `core/semi_auto.py:17-28`

```python
def open_site(self, site: str, query: str = "") -> str:
    url_template = SITE_SEARCH_URLS.get(site, "")
    encoded = quote(query)  # 또는 quote(query, encoding="euc-kr")
    url = url_template.format(query=encoded)
    webbrowser.open(url)
```

`urllib.parse.quote()`로 인코딩하여 URL Injection을 방지하고 있습니다. **양호**.

---

## 9. 데이터베이스 보안 (A02: Cryptographic Failures)

### 판정: Low (로컬 앱 기준)

**위치**: `db/database.py:5-9`

```python
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
```

**양호 사항:**
- Foreign keys 활성화로 참조 무결성 유지
- ON DELETE CASCADE로 고아 레코드 방지

**잔여 위험:**
- SQLite DB 파일 암호화 미적용 (평문 저장)
- DB 파일에 대한 OS 수준 접근 제어 없음
- 업체 정보 (사업자번호, 주소) 등 민감 데이터가 평문으로 저장

**위험도 조정:** 공공기관 업무용 데스크톱 앱으로, 저장 데이터는 구매 견적 정보 수준이므로 Low로 분류합니다. 개인정보보호법 대상 데이터가 포함되지 않는 한 현재 수준으로 충분합니다.

---

## 10. EXE 빌드 보안 (A06: Vulnerable and Outdated Components)

### 10-1. 시드 DB 복사

**위치**: `config.py:56-60`

```python
if getattr(sys, 'frozen', False) and not DB_PATH.exists():
    import shutil
    _seed = _BUNDLE_DIR / "data" / "seed.db"
    if _seed.exists():
        shutil.copy2(str(_seed), str(DB_PATH))
```

**양호:** 첫 실행 시에만 복사하며, 기존 DB가 있으면 덮어쓰지 않습니다.

### 10-2. gen_py 캐시 리디렉션

**위치**: `hwp_generator.py:28-30`

```python
_genpy_dir = os.path.join(tempfile.gettempdir(), "gen_py")
os.makedirs(_genpy_dir, exist_ok=True)
win32com.__gen_path__ = _genpy_dir
```

TEMP 디렉토리의 gen_py 폴더는 다른 사용자도 접근 가능할 수 있으나, gen_py 캐시 자체는 COM 타입 라이브러리 정보만 포함하므로 실질적 위험은 없습니다.

---

## OWASP Top 10 (2021) 체크리스트

| # | 항목 | 적용 여부 | 상태 |
|---|------|----------|------|
| A01 | Broken Access Control | 해당 (파일 시스템) | Medium - 폴더 삭제 경로 미검증 |
| A02 | Cryptographic Failures | 해당 | High - API 키 평문 저장 |
| A03 | Injection | 해당 (SQL) | Pass - 파라미터 바인딩 완전 적용 |
| A04 | Insecure Design | 부분 해당 | Pass - 데스크톱 앱 적절한 설계 |
| A05 | Security Misconfiguration | 해당 (COM) | Medium - 레지스트리 보안 우회 |
| A06 | Vulnerable Components | 해당 | Info - 의존성 버전 고정 필요 |
| A07 | Auth Failures | 비해당 | N/A - 인증 기능 없음 (로컬 앱) |
| A08 | Data Integrity Failures | 해당 | Medium - 설정 파일 무결성 |
| A09 | Logging Failures | 해당 | Medium - 로깅 시스템 부재 |
| A10 | SSRF | 제한적 해당 | Low - webbrowser.open() |

---

## 권장 조치 우선순위

### 즉시 조치 (High)

1. **폴더 삭제 경로 검증** (`tab_history.py`)
   - `shutil.rmtree()` 호출 전 출력 디렉토리 하위 경로인지 검증
   - `resolve()` 후 `startswith()` 비교

2. **API 키 암호화 저장** (`config.py`)
   - `keyring` 라이브러리 또는 Windows DPAPI 활용
   - 또는 최소한 파일 권한 제한

### 차기 릴리스 (Medium)

3. **경로 생성 함수에 `..` 검증 추가** (`config.py`)
   - `make_output_dir()`, `make_output_dir_named()` 함수
   - 최종 경로 resolve 후 base 하위 확인

4. **에러 메시지 정규화**
   - 사용자에게 내부 예외 메시지 노출 방지
   - `logging` 모듈 도입으로 파일 기반 로그 구현

5. **설정 파일 atomic write**
   - 임시파일 쓰기 후 rename으로 파일 손상 방지

6. **HWP 레지스트리 변경 범위 최소화**
   - 앱 종료 시 레지스트리 복원 또는 RegisterModule만 사용

### 백로그 (Low)

7. URL 스킴 화이트리스트 적용 (이력조회 URL 열기)
8. 음수 금액 입력 방지 (UI 레벨 검증)
9. 임시파일 정리 강화 (atexit 핸들러)
10. 의존성 버전 고정 (`requirements.txt` 버전 핀닝)

---

## 부록: 파일별 보안 상태 요약

| 파일 | SQL Injection | Path Traversal | 입력 검증 | 에러 처리 | 비고 |
|------|:---:|:---:|:---:|:---:|------|
| `config.py` | N/A | Medium | N/A | Pass | API 키 평문, 경로 부분 방어 |
| `db/database.py` | Pass | N/A | N/A | Pass | DDL만, 사용자 입력 없음 |
| `db/purchase_repo.py` | Pass | N/A | Pass | Pass | 파라미터 바인딩 완전 |
| `db/inspection_repo.py` | Pass | N/A | Pass | Pass | 파라미터 바인딩 완전 |
| `db/vendor_repo.py` | Pass | N/A | Pass | Pass | 파라미터 바인딩 완전 |
| `ui/tab_purchase.py` | N/A | Low | Pass | Pass | URL 스킴 검증 있음 |
| `ui/tab_history.py` | N/A | High | N/A | Medium | 폴더 삭제 미검증, 에러 노출 |
| `documents/hwp_generator.py` | N/A | Low | Pass | Pass | COM 보안 우회, 제어문자 제거 |
| `core/naver_api.py` | N/A | N/A | Pass | Pass | timeout 적용, HTML 태그 제거 |
| `core/semi_auto.py` | N/A | N/A | Pass | Pass | URL 인코딩 적용 |
