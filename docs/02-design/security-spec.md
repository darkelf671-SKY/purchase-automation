# 보안 평가서 - 결제정보(은행계좌) 기능 추가

**평가일**: 2026-03-12
**평가자**: Security Architect
**대상**: 업체 은행계좌 정보 표시 및 HWP 문서 출력 기능

---

## 1. 평가 요약

| 항목 | 위험도 | 상태 |
|------|--------|------|
| SQL Injection | Low | 양호 - 파라미터 바인딩 사용 중 |
| 저장 데이터 보호 (DB) | Medium | 개선 권장 |
| HWP 템플릿 인젝션 | Low | 양호 - 위험 낮음 |
| 스크린샷 내 계좌 노출 | Medium | 인지 필요 |
| EXE 시드 DB 내 계좌 유출 | High | 조치 필요 |
| API 키 평문 저장 | Medium | 기존 이슈 |
| 설정 파일 평문 저장 | Low | 수용 가능 |

**종합 점수**: 72/100

---

## 2. 상세 분석

### 2.1 SQL Injection (A03) - Low

**현재 상태: 양호**

`vendor_repo.py`의 모든 쿼리가 `:name` 스타일 파라미터 바인딩을 사용하고 있어 SQL Injection 위험이 없음.

```python
# vendor_repo.py - 안전한 파라미터 바인딩 확인
sql = """INSERT INTO vendors (name, ..., account_no)
         VALUES (:name, ..., :account_no)"""
conn.execute(sql, data)
```

`select_by_id`, `delete` 등도 `?` 플레이스홀더 사용 중. 문제 없음.

**단, `build_exe.py`의 시드 DB 생성에서 동적 SQL 구성 발견:**

```python
# build_exe.py:38 - 컬럼명을 동적으로 조합
cols = ", ".join(d.keys())
dst.execute(f"INSERT INTO vendors ({cols}) VALUES ({placeholders})", list(d.values()))
```

이 부분은 `sqlite3.Row`의 키를 직접 사용하므로 외부 입력이 아니며, 빌드 시점 전용 스크립트이므로 실질적 위험은 없음. 다만 코드 일관성 측면에서 개선 가능.

---

### 2.2 저장 데이터 보호 - DB 내 계좌 정보 (A02) - Medium

**현재 상태: 평문 저장**

`vendors` 테이블에 `bank_name`, `account_holder`, `account_no`가 평문으로 저장됨.

**위험 분석:**
- 이 애플리케이션은 **단일 사용자 로컬 데스크톱 앱**
- DB 파일(`purchase.db`)은 사용자 PC 로컬에 위치
- 공공기관 업무용으로 업체 계좌정보는 이미 공문/계약서 등에 공유되는 정보
- 개인 금융정보(개인 계좌)가 아닌 **법인/사업자 계좌**

**판단:**
로컬 데스크톱 앱 특성상 DB 암호화의 실효성이 제한적. SQLite3 파일 자체를 열 수 있는 사용자는 이미 앱에 접근 가능한 사용자와 동일. 다만 PC 분실/도난 시나리오를 고려하면 Windows BitLocker 등 OS 수준 디스크 암호화가 더 적합.

**권장사항:**
1. [선택] Windows BitLocker 활성화 안내 문서 추가
2. [선택] 향후 민감도가 높아지면 `pysqlcipher3` 도입 검토
3. [필수 아님] 현재 수준에서는 평문 저장 수용 가능

---

### 2.3 HWP 템플릿 인젝션 - Low

**현재 상태: 양호**

`hwp_generator.py`의 `_allreplace()` 메서드 분석:

```python
def _allreplace(self, hwp, find: str, replace: str):
    clean = str(replace).replace("\r\n", "\n").replace("\r", "\n")
    clean = "".join(c for c in clean if c in ("\t", "\n") or (ord(c) >= 32))
```

- 제어문자 제거 로직이 이미 적용됨
- HWP AllReplace는 단순 텍스트 치환으로, 매크로/스크립트 실행 경로 없음
- 계좌번호 형식(`140-014-029895`)에 포함될 수 있는 특수문자는 `-`(하이픈) 정도
- `{{`, `}}`가 계좌번호에 포함될 가능성 없음 (자리표시자 충돌 없음)

**판단:** 위험 없음. 추가 조치 불필요.

---

### 2.4 스크린샷 캡처 시 계좌 노출 - Medium

**현재 상태: 인지 필요**

`screenshot.py`의 전체/구역 캡처 기능은 화면에 표시된 모든 정보를 캡처함. 은행계좌 정보가 UI에 표시된 상태에서 캡처 시 스크린샷 이미지에 계좌정보가 포함됨.

**위험 분석:**
- 캡처 목적이 **견적 증빙**이므로 구매탭 캡처 시 계좌정보가 포함될 수 있음
- 캡처 이미지는 `data/screenshots/`에 저장되고, `doc_folder` 출력 폴더에도 복사됨
- 공공기관에서는 증빙 자료가 여러 부서에 회람될 수 있음

**권장사항:**
1. [권장] 캡처 시 은행계좌 영역이 포함되지 않도록 UI 레이아웃 고려 (계좌정보를 별도 섹션/토글로 분리)
2. [참고] 현재 캡처 대상은 주로 쇼핑몰 견적 화면이므로 실제 위험은 제한적

---

### 2.5 EXE 시드 DB 내 계좌 유출 - High

**현재 상태: 조치 필요**

`build_exe.py`가 현재 DB의 `vendors` 테이블 전체를 `seed.db`로 복사하여 EXE에 내장:

```python
# build_exe.py:33-39
vendors = src.execute("SELECT * FROM vendors").fetchall()
for v in vendors:
    d = dict(v)
    ...
    dst.execute(f"INSERT INTO vendors ({cols}) VALUES ({placeholders})", ...)
```

이 과정에서 `bank_name`, `account_holder`, `account_no` 컬럼도 그대로 복사됨.

**위험:**
- EXE 파일이 배포되면 내장된 `seed.db`에서 모든 업체의 은행계좌 정보 추출 가능
- PyInstaller `--onefile`은 실행 시 `_MEIPASS` 임시폴더에 리소스 추출 -> `seed.db` 접근 가능
- EXE를 제3자에게 전달할 경우 의도치 않은 계좌정보 유출

**필수 조치:**

`build_exe.py`의 업체 데이터 복사 시 계좌 관련 컬럼을 제외하거나 공백 처리:

```python
# 권장 수정안
vendors = src.execute("SELECT * FROM vendors").fetchall()
for v in vendors:
    d = dict(v)
    # 민감 정보 제거
    d["bank_name"] = ""
    d["account_holder"] = ""
    d["account_no"] = ""
    ...
```

---

### 2.6 API 키 평문 저장 (기존 이슈) - Medium

**현재 상태: 기존 이슈**

`config.py`에서 네이버 API 키가 `settings.json`에 평문 저장:

```python
NAVER_CLIENT_ID     = _s.get("naver_client_id") or os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = _s.get("naver_client_secret") or os.environ.get("NAVER_CLIENT_SECRET", "")
```

**판단:**
- 환경변수 폴백이 있어 `settings.json` 대신 환경변수 사용 가능
- 로컬 데스크톱 앱이므로 API 키 노출 범위는 해당 PC 사용자로 제한
- 네이버 쇼핑 API 키는 과금 위험이 낮은 무료 API

**권장사항:** 현재 수준 수용 가능. Windows Credential Manager 연동은 과도한 엔지니어링.

---

### 2.7 입력 값 검증 - 계좌번호 형식 - Low

**현재 상태: 검증 없음**

계좌번호에 대한 형식 검증이 없으나, 이는 보안 이슈라기보다 데이터 품질 이슈.

**판단:**
- 은행별 계좌번호 형식이 다양하여 엄격한 정규식 적용이 어려움
- 잘못된 형식 입력 시 보안 위험이 아닌 업무 오류
- HWP 문서에 그대로 출력되므로 사용자가 육안으로 확인 가능

**권장사항:**
1. [선택] 숫자와 하이픈만 허용하는 기본 검증 추가
2. [선택] 계좌번호 길이 제한 (최대 20자)

---

## 3. OWASP Top 10 체크리스트 (데스크톱 앱 적용)

| # | 항목 | 해당 여부 | 상태 |
|---|------|-----------|------|
| A01 | Broken Access Control | 해당 없음 | 단일 사용자 로컬 앱 |
| A02 | Cryptographic Failures | 해당 | Medium - 계좌 평문 저장 (수용 가능) |
| A03 | Injection | 해당 | Low - 파라미터 바인딩 적용됨 |
| A04 | Insecure Design | 해당 없음 | 로컬 앱, 네트워크 노출 없음 |
| A05 | Security Misconfiguration | 해당 | HWP COM 보안 모듈 등록 적절 |
| A06 | Vulnerable Components | 확인 필요 | pywin32, Pillow 등 버전 확인 권장 |
| A07 | Auth Failures | 해당 없음 | 인증 없는 로컬 앱 |
| A08 | Integrity Failures | 해당 | seed.db 계좌정보 포함 (High) |
| A09 | Logging Failures | 해당 없음 | 로컬 앱 |
| A10 | SSRF | 해당 없음 | 서버 없음 |

---

## 4. 조치 우선순위

### 필수 (배포 전)

| # | 항목 | 심각도 | 예상 공수 |
|---|------|--------|-----------|
| 1 | `build_exe.py` 시드 DB에서 계좌정보 제거 | High | 10분 |

### 권장 (다음 스프린트)

| # | 항목 | 심각도 | 예상 공수 |
|---|------|--------|-----------|
| 2 | 캡처 시 계좌정보 영역 분리 검토 | Medium | 1시간 |
| 3 | 계좌번호 기본 형식 검증 추가 | Low | 30분 |

### 참고 (백로그)

| # | 항목 | 심각도 | 비고 |
|---|------|--------|------|
| 4 | 의존성 버전 감사 | Low | pip audit 실행 |
| 5 | DB 암호화 검토 | Low | pysqlcipher3, 필요시 |

---

## 5. 결론

본 프로젝트는 **단일 사용자 로컬 데스크톱 앱**으로, 웹 애플리케이션 대비 공격 표면(attack surface)이 매우 제한적임. 은행계좌 정보 추가에 따른 보안 위험은 전반적으로 **Low~Medium** 수준이며, **유일한 High 이슈는 EXE 시드 DB에 계좌정보가 포함되는 문제**로 `build_exe.py` 수정으로 즉시 해결 가능.

SQL Injection 방어(파라미터 바인딩), HWP 템플릿 치환 시 제어문자 정제 등 기존 보안 조치는 적절히 구현되어 있음.
