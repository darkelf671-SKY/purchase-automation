"""물품구매 자동화 시스템 — 진입점"""
import sys

# Windows DPI 인식 — tkinter 생성 전에 반드시 설정
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from db.database import initialize
from ui.app import App


def main():
    initialize()   # DB 및 테이블 생성
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
