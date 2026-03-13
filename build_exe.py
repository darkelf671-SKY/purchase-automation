"""EXE 빌드 스크립트 — 단일 파일 컴파일 + 시드 데이터 포함"""
import sqlite3
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
SEED_DB = DATA_DIR / "seed.db"
PROD_DB = DATA_DIR / "purchase.db"


def create_seed_db():
    """현재 DB에서 업체·수의계약·기안템플릿 데이터만 추출한 시드 DB 생성"""
    if SEED_DB.exists():
        SEED_DB.unlink()

    # 원본 DB 스키마 그대로 복제
    src = sqlite3.connect(PROD_DB)
    src.row_factory = sqlite3.Row
    dst = sqlite3.connect(SEED_DB)

    # 스키마 복제 (테이블 생성 SQL 추출)
    tables = src.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL "
        "AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    for t in tables:
        dst.execute(t[0])

    # 업체 데이터
    vendors = src.execute("SELECT * FROM vendors").fetchall()
    for v in vendors:
        d = dict(v)
        cols = ", ".join(d.keys())
        placeholders = ", ".join(["?"] * len(d))
        dst.execute(f"INSERT INTO vendors ({cols}) VALUES ({placeholders})",
                    list(d.values()))

    # 수의계약 사유 데이터
    soles = src.execute("SELECT * FROM sole_contract_reasons").fetchall()
    for s in soles:
        d = dict(s)
        cols = ", ".join(d.keys())
        placeholders = ", ".join(["?"] * len(d))
        dst.execute(
            f"INSERT INTO sole_contract_reasons ({cols}) VALUES ({placeholders})",
            list(d.values()))

    # 기안 템플릿 데이터
    templates = src.execute("SELECT * FROM draft_templates").fetchall()
    for t in templates:
        d = dict(t)
        cols = ", ".join(d.keys())
        placeholders = ", ".join(["?"] * len(d))
        dst.execute(
            f"INSERT INTO draft_templates ({cols}) VALUES ({placeholders})",
            list(d.values()))

    dst.commit()
    dst.close()
    src.close()

    count_v = len(vendors)
    count_s = len(soles)
    count_t = len(templates)
    print(f"[OK] 시드 DB 생성: {SEED_DB}")
    print(f"     업체 {count_v}건, 수의계약 사유 {count_s}건, 기안 템플릿 {count_t}건")
    return SEED_DB


def build_exe():
    """PyInstaller --onefile 빌드"""
    seed = create_seed_db()

    # 템플릿 파일 (HWP/Excel) — 읽기전용 리소스로 번들
    template_dir = ROOT / "documents" / "templates"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "구매기안자동화",
        # 읽기전용 리소스 번들
        "--add-data", f"{template_dir};documents/templates",
        # 시드 DB 번들
        "--add-data", f"{seed};data",
        # 아이콘 (없으면 무시)
        # "--icon", "icon.ico",
        "--noconfirm",
        "--clean",
        str(ROOT / "main.py"),
    ]

    print("\n[BUILD] PyInstaller 실행 중...")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT))

    if result.returncode == 0:
        exe_path = ROOT / "dist" / "구매기안자동화.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\n{'='*50}")
            print(f"[SUCCESS] EXE 빌드 완료!")
            print(f"  파일: {exe_path}")
            print(f"  크기: {size_mb:.1f} MB")
            print(f"{'='*50}")
            print(f"\n[배포 방법]")
            print(f"  1. dist/구매기안자동화.exe 파일만 복사")
            print(f"  2. 다른 PC에서 실행하면 자동으로:")
            print(f"     - data/ 폴더 생성")
            print(f"     - 시드 DB (업체/수의계약/템플릿) 자동 복사")
            print(f"     - HWP 템플릿은 EXE 내장")
        else:
            print("[ERROR] EXE 파일을 찾을 수 없습니다.")
    else:
        print(f"[ERROR] PyInstaller 빌드 실패 (exit code: {result.returncode})")

    # 시드 DB 정리
    if seed.exists():
        seed.unlink()
        print("[CLEANUP] 시드 DB 삭제")


if __name__ == "__main__":
    build_exe()
