import time
from datetime import datetime
from pathlib import Path
from PIL import ImageGrab, ImageDraw, ImageFont
from config import SCREENSHOT_DIR


def _add_timestamp_watermark(img):
    """캡처 이미지 우측 상단에 현재 일시 워터마크 삽입 (증빙용)"""
    draw = ImageDraw.Draw(img)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = f"캡처일시: {timestamp}"

    try:
        font = ImageFont.truetype("malgun.ttf", 16)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    pad = 8
    # 우측 상단 — 이미지 폭이 텍스트보다 좁으면 좌측 정렬
    x = max(pad, img.width - tw - pad)
    y = pad

    # 반투명 배경 + 흰색 텍스트
    draw.rectangle([x - pad, y - pad // 2, x + tw + pad, y + th + pad // 2],
                   fill=(0, 0, 0))
    draw.text((x, y), text, fill=(255, 255, 255), font=font)
    return img


def grab_clean_screen() -> "Image":
    """깨끗한 화면 캡처 (오버레이 없이). 호출 전 윈도우 숨김 필수."""
    time.sleep(0.5)
    return ImageGrab.grab()


def capture(save_path: str | Path = None) -> str:
    """전체 화면 캡처 + 일시 워터마크.
    save_path 지정 시 해당 경로에 저장 (기존 파일 자동 삭제).
    """
    if save_path is None:
        save_path = SCREENSHOT_DIR / "temp_capture.png"

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    if save_path.exists():
        save_path.unlink()

    img = grab_clean_screen()
    img = _add_timestamp_watermark(img)
    img.save(save_path)
    return str(save_path)


def capture_region(full_img, parent=None, save_path: str | Path = None) -> str | None:
    """구역 선택 캡처 (스니핑 툴 방식) + 일시 워터마크.

    full_img: 사전 캡처된 깨끗한 원본 이미지 (ImageGrab.grab() 결과).
              호출부에서 윈도우 숨김 후 grab_clean_screen()으로 획득.
    오버레이는 tkinter 화면 크기에 맞추고, 크롭 좌표는 이미지 해상도로 변환.
    취소(ESC) 시 None 반환.
    """
    import tkinter as tk
    from PIL import ImageTk, ImageEnhance

    result = [None]
    root = parent.winfo_toplevel() if parent else None
    sel_win = tk.Toplevel(root) if root else tk.Tk()
    sel_win.overrideredirect(True)
    sel_win.attributes("-topmost", True)

    # tkinter 화면 크기 (논리 해상도) — 오버레이 창 크기 기준
    scr_w = sel_win.winfo_screenwidth()
    scr_h = sel_win.winfo_screenheight()
    sel_win.geometry(f"{scr_w}x{scr_h}+0+0")

    # 이미지 해상도와 화면 해상도의 비율 (DPI 스케일링 대응)
    img_w, img_h = full_img.width, full_img.height
    scale_x = img_w / scr_w
    scale_y = img_h / scr_h

    # 오버레이용 어두운 이미지 — 화면 크기에 맞춤
    dark_img = ImageEnhance.Brightness(full_img).enhance(0.35)
    if img_w != scr_w or img_h != scr_h:
        dark_img = dark_img.resize((scr_w, scr_h))

    sel_win._tk_img = ImageTk.PhotoImage(dark_img)

    canvas = tk.Canvas(sel_win, cursor="cross", width=scr_w, height=scr_h,
                       bd=0, highlightthickness=0, bg="black")
    canvas.pack(fill="both", expand=True)
    canvas.create_image(0, 0, anchor="nw", image=sel_win._tk_img)
    canvas.create_text(
        scr_w // 2, 28,
        text="드래그하여 캡처 영역을 선택하세요   (ESC: 취소)",
        fill="yellow", font=("Arial", 13, "bold"),
    )

    start = [0, 0]
    rect_id = [None]

    def on_press(e):
        start[0], start[1] = e.x, e.y
        if rect_id[0]:
            canvas.delete(rect_id[0])

    def on_drag(e):
        if rect_id[0]:
            canvas.delete(rect_id[0])
        rect_id[0] = canvas.create_rectangle(
            start[0], start[1], e.x, e.y,
            outline="red", width=2,
        )

    def on_release(e):
        # 논리 좌표 → 물리 좌표 변환 (DPI 스케일링 대응)
        x1 = int(min(start[0], e.x) * scale_x)
        y1 = int(min(start[1], e.y) * scale_y)
        x2 = int(max(start[0], e.x) * scale_x)
        y2 = int(max(start[1], e.y) * scale_y)
        sel_win.destroy()
        if x2 - x1 > 5 and y2 - y1 > 5:
            cropped = full_img.crop((x1, y1, x2, y2))
            cropped = _add_timestamp_watermark(cropped)
            sp = Path(save_path) if save_path else SCREENSHOT_DIR / "temp_capture_region.png"
            sp.parent.mkdir(parents=True, exist_ok=True)
            if sp.exists():
                sp.unlink()
            cropped.save(sp)
            result[0] = str(sp)

    canvas.bind("<ButtonPress-1>",   on_press)
    canvas.bind("<B1-Motion>",       on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    sel_win.bind("<Escape>", lambda e: sel_win.destroy())
    sel_win.focus_force()
    sel_win.wait_window()
    return result[0]


def make_screenshot_name(slot: int, vendor_name: str, ext: str = ".png") -> str:
    """견적 파일명 생성. 예: 1.견적서_쿠팡.png  /  2.견적서_업체명.pdf"""
    safe = vendor_name.replace("/", "_").replace("\\", "_").strip() or "업체"
    return f"{slot}.견적서_{safe}{ext}"


def cleanup(path: str | Path):
    """파일이 존재하면 삭제"""
    p = Path(path)
    if p.exists():
        try:
            p.unlink()
        except Exception:
            pass
