from __future__ import annotations

import argparse
import calendar
import ctypes
import json
import os
import queue
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from ctypes import wintypes

import tkinter as tk
from tkinter import messagebox

try:
    import winreg
except ImportError:  # pragma: no cover - only used when inspecting the project off Windows
    winreg = None


APP_NAME = "DateProgressBar"
APP_TITLE = "Date Progress Bar"
WINDOW_WIDTH = 470
WINDOW_HEIGHT = 154
MIN_WINDOW_WIDTH = 350
MIN_WINDOW_HEIGHT = 126
MAX_WINDOW_WIDTH = 900
MAX_WINDOW_HEIGHT = 300
GRADIENT_SEGMENTS = 36
REFRESH_INTERVALS = {
    "day": 5_000,
    "month": 30_000,
    "year": 60_000,
    "custom": 30_000,
}
DAY_THEME_START_HOUR = 6
NIGHT_THEME_START_HOUR = 18
TRANSPARENT_COLOR = "#ff00ff"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
ERROR_ALREADY_EXISTS = 183
HWND_BOTTOM = 1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SMTO_NORMAL = 0x0000
GA_ROOT = 2
instance_mutex: int | None = None


@dataclass(frozen=True)
class Theme:
    label: str
    background: str
    panel: str
    border: str
    track: str
    text_primary: str
    text_muted: str
    text_faint: str
    accent_start: str
    accent_end: str
    mood: str


THEMES = {
    "rainy_night": Theme(
        label="Mưa đêm",
        background="#101722",
        panel="#17212e",
        border="#34495e",
        track="#263647",
        text_primary="#f1f6fa",
        text_muted="#a7bac8",
        text_faint="#718797",
        accent_start="#73a9bf",
        accent_end="#607a9b",
        mood="Có những đêm, nỗi buồn ở lại lâu hơn cả cơn mưa.",
    ),
    "cold_ash": Theme(
        label="Tro lạnh",
        background="#171717",
        panel="#222222",
        border="#454545",
        track="#353535",
        text_primary="#f3f3f1",
        text_muted="#b8b8b2",
        text_faint="#7c7c78",
        accent_start="#c4c4bd",
        accent_end="#73736f",
        mood="Có những điều đã nguội lạnh, nhưng chạm vào vẫn đau.",
    ),
    "old_sunset": Theme(
        label="Hoàng hôn cũ",
        background="#21171e",
        panel="#30202a",
        border="#68485b",
        track="#4a3340",
        text_primary="#fff3f1",
        text_muted="#d4b1b6",
        text_faint="#98737e",
        accent_start="#d18b92",
        accent_end="#8c668b",
        mood="Hoàng hôn nào rồi cũng tắt, như người từng hứa sẽ ở lại.",
    ),
    "deep_sea": Theme(
        label="Biển sâu",
        background="#0d1720",
        panel="#142630",
        border="#315563",
        track="#203d49",
        text_primary="#edf9f8",
        text_muted="#9abec1",
        text_faint="#608d94",
        accent_start="#67b7b2",
        accent_end="#477d91",
        mood="Có những nỗi buồn chìm quá sâu để gọi thành tên.",
    ),
    "violet_memory": Theme(
        label="Ký ức tím",
        background="#181526",
        panel="#241f35",
        border="#51466f",
        track="#39324f",
        text_primary="#f8f4ff",
        text_muted="#bdb1d5",
        text_faint="#81749d",
        accent_start="#ad91d2",
        accent_end="#766aab",
        mood="Thời gian không chữa lành, chỉ dạy ta cách im lặng.",
    ),
}

THEME_TEXT = {
    "rainy_night": {
        "en": ("Rainy Night", "Some nights, sorrow stays longer than the rain."),
        "ja": ("雨の夜", "雨が止んでも、悲しみだけは夜に残る。"),
    },
    "cold_ash": {
        "en": ("Cold Ash", "Some things have gone cold, yet still hurt to touch."),
        "ja": ("冷たい灰", "冷めてしまった記憶ほど、触れると痛い。"),
    },
    "old_sunset": {
        "en": ("Old Sunset", "Every sunset fades, like those who once promised to stay."),
        "ja": ("遠い夕暮れ", "夕暮れはいつか消える。ずっとそばにいると言った人のように。"),
    },
    "deep_sea": {
        "en": ("Deep Sea", "Some sorrows sink too deep to ever be named."),
        "ja": ("深い海", "深く沈みすぎて、名前さえつけられない悲しみがある。"),
    },
    "violet_memory": {
        "en": ("Violet Memory", "Time does not heal; it only teaches us how to stay silent."),
        "ja": ("紫の記憶", "時間は傷を癒やさない。ただ、沈黙の仕方を教えるだけだ。"),
    },
}

TEXT = {
    "vi": {
        "mode_year": "Tiến độ năm",
        "mode_month": "Tiến độ tháng",
        "mode_day": "Tiến độ hôm nay",
        "mode_custom": "Khoảng thời gian tùy chọn",
        "custom_ranges": "Khoảng thời gian",
        "custom_add": "Thêm khoảng thời gian",
        "custom_edit": "Sửa khoảng đang chọn",
        "custom_delete": "Xóa khoảng đang chọn",
        "custom_empty": "Chưa có khoảng thời gian nào",
        "sad_style": "Style buồn",
        "theme_scheduler": "Tự đổi theme theo giờ",
        "language": "Ngôn ngữ",
        "always_on_top": "Luôn nổi trên màn hình",
        "start_with_windows": "Khởi động cùng Windows",
        "toggle_widget": "Ẩn / hiện widget",
        "quit": "Thoát",
        "title_year": "TIẾN ĐỘ NĂM {year}",
        "title_month": "TIẾN ĐỘ THÁNG {month:02d}/{year}",
        "title_day": "TIẾN ĐỘ HÔM NAY  ·  {date}",
        "title_custom": "KHOẢNG THỜI GIAN TÙY CHỌN",
        "detail": "{elapsed} đã qua   ·   {remaining} còn lại",
        "days": "{value} ngày",
        "hours_minutes": "{hours} giờ {minutes} phút",
        "dialog_title": "Khoảng thời gian tùy chọn",
        "dialog_name": "Tên hiển thị",
        "dialog_start": "Bắt đầu",
        "dialog_end": "Kết thúc",
        "dialog_hint": "Định dạng: YYYY-MM-DD HH:MM",
        "save": "Lưu",
        "cancel": "Hủy",
        "invalid_range": "Thời gian kết thúc phải sau thời gian bắt đầu.",
        "invalid_datetime": "Ngày giờ chưa đúng định dạng YYYY-MM-DD HH:MM.",
        "invalid_name": "Hãy nhập tên hiển thị cho khoảng thời gian.",
        "delete_title": "Xóa khoảng thời gian",
        "delete_confirm": "Xóa khoảng thời gian \"{name}\"?",
    },
    "en": {
        "mode_year": "Year progress",
        "mode_month": "Month progress",
        "mode_day": "Today's progress",
        "mode_custom": "Custom interval",
        "custom_ranges": "Saved intervals",
        "custom_add": "Add interval",
        "custom_edit": "Edit selected interval",
        "custom_delete": "Delete selected interval",
        "custom_empty": "No saved intervals",
        "sad_style": "Melancholy style",
        "theme_scheduler": "Schedule theme by time",
        "language": "Language",
        "always_on_top": "Always on top",
        "start_with_windows": "Start with Windows",
        "toggle_widget": "Hide / show widget",
        "quit": "Quit",
        "title_year": "YEAR PROGRESS {year}",
        "title_month": "MONTH PROGRESS {month:02d}/{year}",
        "title_day": "TODAY'S PROGRESS  ·  {date}",
        "title_custom": "CUSTOM INTERVAL",
        "detail": "{elapsed} elapsed   ·   {remaining} remaining",
        "days": "{value} days",
        "hours_minutes": "{hours} hr {minutes} min",
        "dialog_title": "Custom interval",
        "dialog_name": "Display name",
        "dialog_start": "Start",
        "dialog_end": "End",
        "dialog_hint": "Format: YYYY-MM-DD HH:MM",
        "save": "Save",
        "cancel": "Cancel",
        "invalid_range": "The end time must be later than the start time.",
        "invalid_datetime": "Use the date format YYYY-MM-DD HH:MM.",
        "invalid_name": "Enter a display name for this interval.",
        "delete_title": "Delete interval",
        "delete_confirm": "Delete the interval \"{name}\"?",
    },
    "ja": {
        "mode_year": "一年の進捗",
        "mode_month": "今月の進捗",
        "mode_day": "今日の進捗",
        "mode_custom": "カスタム期間",
        "custom_ranges": "保存した期間",
        "custom_add": "期間を追加",
        "custom_edit": "選択中の期間を編集",
        "custom_delete": "選択中の期間を削除",
        "custom_empty": "保存した期間はありません",
        "sad_style": "物悲しいスタイル",
        "theme_scheduler": "時間帯でテーマを自動切り替え",
        "language": "言語",
        "always_on_top": "常に手前に表示",
        "start_with_windows": "Windows の起動時に開始",
        "toggle_widget": "ウィジェットを表示 / 非表示",
        "quit": "終了",
        "title_year": "{year}年の進捗",
        "title_month": "{year}年{month}月の進捗",
        "title_day": "今日の進捗  ·  {date}",
        "title_custom": "カスタム期間",
        "detail": "{elapsed}経過   ·   残り{remaining}",
        "days": "{value}日",
        "hours_minutes": "{hours}時間{minutes}分",
        "dialog_title": "カスタム期間",
        "dialog_name": "表示名",
        "dialog_start": "開始日時",
        "dialog_end": "終了日時",
        "dialog_hint": "形式: YYYY-MM-DD HH:MM",
        "save": "保存",
        "cancel": "キャンセル",
        "invalid_range": "終了日時は開始日時より後に設定してください。",
        "invalid_datetime": "日時は YYYY-MM-DD HH:MM の形式で入力してください。",
        "invalid_name": "期間の表示名を入力してください。",
        "delete_title": "期間を削除",
        "delete_confirm": "「{name}」を削除しますか？",
    },
}


@dataclass(frozen=True)
class Progress:
    title: str
    detail: str
    ratio: float


def blend_color(start: str, end: str, ratio: float) -> str:
    ratio = min(max(ratio, 0.0), 1.0)
    start_rgb = tuple(int(start[index : index + 2], 16) for index in (1, 3, 5))
    end_rgb = tuple(int(end[index : index + 2], 16) for index in (1, 3, 5))
    mixed = tuple(round(a + (b - a) * ratio) for a, b in zip(start_rgb, end_rgb))
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def tr(language: str, key: str, **values: Any) -> str:
    text = TEXT.get(language, TEXT["vi"]).get(key, TEXT["vi"][key])
    return text.format(**values)


def theme_label(theme_key: str, language: str) -> str:
    theme = THEMES[theme_key]
    if language == "vi":
        return theme.label
    return THEME_TEXT[theme_key][language][0]


def theme_quote(theme_key: str, language: str) -> str:
    theme = THEMES[theme_key]
    if language == "vi":
        return theme.mood
    return THEME_TEXT[theme_key][language][1]


def scheduled_theme_key(now: datetime) -> str:
    if DAY_THEME_START_HOUR <= now.hour < NIGHT_THEME_START_HOUR:
        return "old_sunset"
    return "rainy_night"


def parse_datetime_input(value: str) -> datetime:
    value = value.strip()
    for date_format in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            pass
    raise ValueError("Unsupported datetime format")


def format_datetime_input(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


def format_duration(duration: timedelta, mode: str, language: str) -> str:
    seconds = max(0, int(duration.total_seconds()))
    if mode == "day" or (mode == "custom" and seconds < 172_800):
        hours, remainder = divmod(seconds, 3600)
        minutes = remainder // 60
        return tr(language, "hours_minutes", hours=hours, minutes=minutes)
    days = seconds // 86400
    if language == "en" and days == 1:
        return "1 day"
    return tr(language, "days", value=days)


def new_custom_range(title: str, start: str, end: str) -> dict[str, str]:
    return {
        "id": uuid.uuid4().hex[:12],
        "title": title.strip(),
        "start": start,
        "end": end,
    }


def active_custom_range(settings: dict[str, Any]) -> dict[str, str] | None:
    ranges = settings.get("custom_ranges", [])
    active_id = settings.get("active_custom_id")
    for custom_range in ranges:
        if custom_range["id"] == active_id:
            return custom_range
    return ranges[0] if ranges else None


def calculate_progress(
    now: datetime,
    mode: str,
    language: str = "vi",
    settings: dict[str, Any] | None = None,
) -> Progress:
    if mode == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        if language == "ja":
            date_label = f"{now.month}月{now.day}日"
        elif language == "en":
            date_label = now.strftime("%b %d")
        else:
            date_label = now.strftime("%d/%m")
        title = tr(language, "title_day", date=date_label)
    elif mode == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            end = start.replace(year=now.year + 1, month=1)
        else:
            end = start.replace(month=now.month + 1)
        title = tr(language, "title_month", month=now.month, year=now.year)
    elif mode == "custom" and settings is not None:
        custom_range = active_custom_range(settings)
        if custom_range is None:
            start = now
            end = now + timedelta(days=1)
            title = tr(language, "title_custom")
        else:
            start = datetime.fromisoformat(custom_range["start"])
            end = datetime.fromisoformat(custom_range["end"])
            title = custom_range["title"]
    else:
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=now.year + 1)
        title = tr(language, "title_year", year=now.year)

    total_seconds = (end - start).total_seconds()
    total = end - start
    elapsed = min(max(now - start, timedelta()), total)
    remaining = min(max(end - now, timedelta()), total)
    ratio = min(max(elapsed.total_seconds() / total_seconds, 0.0), 1.0)
    duration_mode = "month" if mode == "custom" and total_seconds >= 172_800 else mode
    detail = tr(
        language,
        "detail",
        elapsed=format_duration(elapsed, duration_mode, language),
        remaining=format_duration(remaining, duration_mode, language),
    )
    return Progress(title=title, detail=detail, ratio=ratio)


def enable_high_dpi() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass


def settings_path() -> Path:
    app_data = os.environ.get("LOCALAPPDATA")
    root = Path(app_data) if app_data else Path.home() / ".date_progress_bar"
    return root / APP_NAME / "settings.json"


def load_settings() -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "mode": "year",
        "language": "vi",
        "theme": "rainy_night",
        "theme_scheduler": False,
        "start_with_windows": True,
        "always_on_top": True,
        "width": WINDOW_WIDTH,
        "height": WINDOW_HEIGHT,
        "custom_ranges": [],
        "active_custom_id": "",
    }
    path = settings_path()
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return defaults
    settings = {**defaults, **stored}
    if settings["language"] not in TEXT:
        settings["language"] = "vi"
    if settings["theme"] not in THEMES:
        settings["theme"] = "rainy_night"
    settings["theme_scheduler"] = bool(settings.get("theme_scheduler", False))
    if settings["mode"] not in ("year", "month", "day", "custom"):
        settings["mode"] = "year"
    ranges = settings.get("custom_ranges")
    if not isinstance(ranges, list):
        ranges = []
    legacy_title = str(settings.get("custom_title", "")).strip()
    legacy_start = settings.get("custom_start")
    legacy_end = settings.get("custom_end")
    if not ranges and legacy_title and legacy_start and legacy_end:
        ranges = [new_custom_range(legacy_title, legacy_start, legacy_end)]

    valid_ranges = []
    for custom_range in ranges:
        try:
            title = str(custom_range["title"]).strip()
            start = datetime.fromisoformat(custom_range["start"])
            end = datetime.fromisoformat(custom_range["end"])
            range_id = str(custom_range["id"])
            if not title or end <= start:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            continue
        valid_ranges.append(
            {
                "id": range_id,
                "title": title,
                "start": start.isoformat(timespec="minutes"),
                "end": end.isoformat(timespec="minutes"),
            }
        )
    settings["custom_ranges"] = valid_ranges
    active_ids = {custom_range["id"] for custom_range in valid_ranges}
    if settings.get("active_custom_id") not in active_ids:
        settings["active_custom_id"] = valid_ranges[0]["id"] if valid_ranges else ""
    for legacy_key in ("custom_title", "custom_start", "custom_end"):
        settings.pop(legacy_key, None)
    if settings["mode"] == "custom" and not valid_ranges:
        settings["mode"] = "day"
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def pythonw_path() -> Path:
    executable = Path(sys.executable)
    candidate = executable.with_name("pythonw.exe")
    return candidate if candidate.exists() else executable


def startup_command() -> str:
    if getattr(sys, "frozen", False):
        return subprocess.list2cmdline([str(Path(sys.executable).resolve())])
    return subprocess.list2cmdline([str(pythonw_path()), str(Path(__file__).resolve())])


def set_startup_enabled(enabled: bool) -> bool:
    if winreg is None:
        return False
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, startup_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return enabled
    except OSError:
        return False


def is_startup_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
        return value == startup_command()
    except OSError:
        return False


def claim_single_instance() -> bool:
    global instance_mutex
    if sys.platform != "win32":
        return True
    instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, APP_NAME)
    return ctypes.windll.kernel32.GetLastError() != ERROR_ALREADY_EXISTS


def desktop_parent_window() -> int:
    if sys.platform != "win32":
        return 0
    user32 = ctypes.windll.user32
    user32.FindWindowW.restype = wintypes.HWND
    user32.FindWindowExW.restype = wintypes.HWND
    progman = user32.FindWindowW("Progman", None)
    if progman:
        result = wintypes.DWORD()
        user32.SendMessageTimeoutW(
            progman,
            0x052C,
            0,
            0,
            SMTO_NORMAL,
            1_000,
            ctypes.byref(result),
        )

    workerw = wintypes.HWND()
    enum_proc_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM,
    )

    def find_workerw(hwnd: int, _lparam: int) -> bool:
        shell_view = user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
        if shell_view:
            workerw.value = user32.FindWindowExW(None, hwnd, "WorkerW", None)
        return True

    enum_proc = enum_proc_type(find_workerw)
    user32.EnumWindows(enum_proc, 0)
    return workerw.value or progman or 0


def virtual_screen_bounds() -> tuple[int, int, int, int]:
    if sys.platform != "win32":
        return 0, 0, 0, 0
    user32 = ctypes.windll.user32
    return (
        user32.GetSystemMetrics(76),
        user32.GetSystemMetrics(77),
        user32.GetSystemMetrics(78),
        user32.GetSystemMetrics(79),
    )


def tray_icon_path() -> Path:
    return settings_path().with_name("tray.ico")


def ensure_tray_icon() -> Path | None:
    path = tray_icon_path()
    if path.exists():
        return path
    try:
        from PIL import Image, ImageDraw

        path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            (3, 3, 61, 61),
            radius=16,
            fill="#101722",
            outline="#73a9bf",
            width=3,
        )
        draw.arc((18, 13, 48, 43), 65, 285, fill="#d9ecf2", width=5)
        draw.ellipse((28, 17, 46, 35), fill="#101722")
        draw.rounded_rectangle((14, 45, 50, 49), radius=2, fill="#34495e")
        draw.rounded_rectangle((14, 45, 37, 49), radius=2, fill="#73a9bf")
        image.save(path, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64)])
        return path
    except (ImportError, OSError):
        return None


class NativeTrayIcon:
    WM_TRAY_CALLBACK = 0x8001
    WM_LBUTTONUP = 0x0202
    WM_RBUTTONUP = 0x0205
    WM_CLOSE = 0x0010
    WM_DESTROY = 0x0002
    NIM_ADD = 0x00000000
    NIM_DELETE = 0x00000002
    NIF_MESSAGE = 0x00000001
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004
    IMAGE_ICON = 1
    LR_LOADFROMFILE = 0x00000010
    LR_DEFAULTSIZE = 0x00000040

    class WNDCLASSW(ctypes.Structure):
        _fields_ = [
            ("style", wintypes.UINT),
            ("lpfnWndProc", ctypes.c_void_p),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", wintypes.HINSTANCE),
            ("hIcon", wintypes.HICON),
            ("hCursor", wintypes.HANDLE),
            ("hbrBackground", wintypes.HBRUSH),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
        ]

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hWnd", wintypes.HWND),
            ("uID", wintypes.UINT),
            ("uFlags", wintypes.UINT),
            ("uCallbackMessage", wintypes.UINT),
            ("hIcon", wintypes.HICON),
            ("szTip", wintypes.WCHAR * 128),
            ("dwState", wintypes.DWORD),
            ("dwStateMask", wintypes.DWORD),
            ("szInfo", wintypes.WCHAR * 256),
            ("uTimeoutOrVersion", wintypes.UINT),
            ("szInfoTitle", wintypes.WCHAR * 64),
            ("dwInfoFlags", wintypes.DWORD),
        ]

    def __init__(self, app: "ProgressBarApp") -> None:
        self.events: queue.SimpleQueue[str] = queue.SimpleQueue()
        self.ready = threading.Event()
        self.startup_error: OSError | None = None
        self.hwnd = 0
        self.hicon = 0
        self.loaded_icon = False
        self.class_name = f"{APP_NAME}TrayWindow{os.getpid()}"
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        if not self.ready.wait(timeout=2) or self.startup_error is not None:
            raise self.startup_error or OSError("Timed out while creating the tray icon")

    def run(self) -> None:
        self.user32 = ctypes.windll.user32
        self.shell32 = ctypes.windll.shell32
        self.kernel32 = ctypes.windll.kernel32
        self.kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        self.kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self.user32.RegisterClassW.restype = wintypes.ATOM
        self.user32.RegisterClassW.argtypes = [ctypes.POINTER(self.WNDCLASSW)]
        self.user32.CreateWindowExW.restype = wintypes.HWND
        self.user32.CreateWindowExW.argtypes = [
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.HMENU,
            wintypes.HINSTANCE,
            wintypes.LPVOID,
        ]
        self.user32.DefWindowProcW.restype = ctypes.c_ssize_t
        self.user32.DefWindowProcW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            ctypes.c_size_t,
            ctypes.c_ssize_t,
        ]
        self.user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
        self.callback_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            wintypes.HWND,
            wintypes.UINT,
            ctypes.c_size_t,
            ctypes.c_ssize_t,
        )
        self.callback = self.callback_type(self.window_proc)
        self.taskbar_created_message = self.user32.RegisterWindowMessageW("TaskbarCreated")
        instance = self.kernel32.GetModuleHandleW(None)
        registered = False
        window_class = self.WNDCLASSW()
        window_class.lpfnWndProc = ctypes.cast(self.callback, ctypes.c_void_p)
        window_class.hInstance = instance
        window_class.lpszClassName = self.class_name
        try:
            if not self.user32.RegisterClassW(ctypes.byref(window_class)):
                raise OSError("Could not register the tray window class")
            registered = True
            self.hwnd = self.user32.CreateWindowExW(
                0,
                self.class_name,
                APP_TITLE,
                0,
                0,
                0,
                0,
                0,
                None,
                None,
                instance,
                None,
            )
            if not self.hwnd:
                raise OSError("Could not create the tray message window")
            self.hicon = self.load_icon()
            self.data = self.NOTIFYICONDATAW()
            self.data.cbSize = ctypes.sizeof(self.NOTIFYICONDATAW)
            self.data.hWnd = self.hwnd
            self.data.uID = 1
            self.data.uFlags = self.NIF_MESSAGE | self.NIF_ICON | self.NIF_TIP
            self.data.uCallbackMessage = self.WM_TRAY_CALLBACK
            self.data.hIcon = self.hicon
            self.data.szTip = APP_TITLE
            if not self.add():
                raise OSError("Windows Explorer did not accept the tray icon")
            self.ready.set()

            message = wintypes.MSG()
            while self.user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                self.user32.TranslateMessage(ctypes.byref(message))
                self.user32.DispatchMessageW(ctypes.byref(message))
        except Exception as error:
            self.startup_error = OSError(str(error))
            self.ready.set()
        finally:
            if self.hwnd and hasattr(self, "data"):
                self.shell32.Shell_NotifyIconW(self.NIM_DELETE, ctypes.byref(self.data))
            if self.loaded_icon and self.hicon:
                self.user32.DestroyIcon(self.hicon)
            if self.hwnd:
                self.user32.DestroyWindow(self.hwnd)
            if registered:
                self.user32.UnregisterClassW(self.class_name, instance)
            self.hwnd = 0

    def add(self) -> bool:
        return bool(self.shell32.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(self.data)))

    def load_icon(self) -> int:
        self.user32.LoadImageW.restype = wintypes.HANDLE
        self.user32.LoadIconW.restype = wintypes.HICON
        path = ensure_tray_icon()
        if path is not None:
            icon = self.user32.LoadImageW(
                None,
                str(path),
                self.IMAGE_ICON,
                0,
                0,
                self.LR_LOADFROMFILE | self.LR_DEFAULTSIZE,
            )
            if icon:
                self.loaded_icon = True
                return icon
        return self.user32.LoadIconW(None, ctypes.c_void_p(32512))

    def window_proc(
        self,
        hwnd: int,
        message: int,
        wparam: int,
        lparam: int,
    ) -> int:
        if message == self.taskbar_created_message:
            self.add()
            return 0
        if message == self.WM_TRAY_CALLBACK:
            event = lparam & 0xFFFF
            if event == self.WM_LBUTTONUP:
                self.events.put("show")
            elif event == self.WM_RBUTTONUP:
                self.events.put("menu")
            return 0
        if message == self.WM_CLOSE:
            self.user32.DestroyWindow(hwnd)
            return 0
        if message == self.WM_DESTROY:
            self.user32.PostQuitMessage(0)
            return 0
        return self.user32.DefWindowProcW(hwnd, message, wparam, lparam)

    def remove(self) -> None:
        if self.hwnd:
            self.user32.PostMessageW(self.hwnd, self.WM_CLOSE, 0, 0)
            self.thread.join(timeout=1)


class CustomRangeDialog:
    def __init__(
        self,
        app: "ProgressBarApp",
        custom_range: dict[str, str] | None = None,
    ) -> None:
        self.app = app
        self.language = app.language_var.get()
        self.custom_id = custom_range["id"] if custom_range else None
        now = datetime.now().replace(second=0, microsecond=0)
        self.window = tk.Toplevel(app.root)
        self.window.title(tr(self.language, "dialog_title"))
        self.window.configure(bg=app.theme.background)
        self.window.resizable(False, False)
        self.window.transient(app.root)
        self.window.attributes("-topmost", True)
        self.window.grab_set()

        self.name_var = tk.StringVar(value=custom_range["title"] if custom_range else "")
        self.start_var = tk.StringVar(
            value=format_datetime_input(
                custom_range["start"] if custom_range else now.isoformat(timespec="minutes")
            )
        )
        self.end_var = tk.StringVar(
            value=format_datetime_input(
                custom_range["end"]
                if custom_range
                else (now + timedelta(days=30)).isoformat(timespec="minutes")
            )
        )

        self.add_entry(0, "dialog_name", self.name_var)
        self.add_entry(1, "dialog_start", self.start_var)
        self.add_entry(2, "dialog_end", self.end_var)
        tk.Label(
            self.window,
            text=tr(self.language, "dialog_hint"),
            bg=app.theme.background,
            fg=app.theme.text_faint,
            font=app.ui_font(9),
        ).grid(row=3, column=0, columnspan=2, padx=16, pady=(0, 12), sticky="w")

        button_frame = tk.Frame(self.window, bg=app.theme.background)
        button_frame.grid(row=4, column=0, columnspan=2, padx=16, pady=(0, 16), sticky="e")
        tk.Button(
            button_frame,
            text=tr(self.language, "cancel"),
            command=self.window.destroy,
            padx=12,
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            button_frame,
            text=tr(self.language, "save"),
            command=self.save,
            padx=12,
        ).pack(side="left")

        self.window.bind("<Escape>", lambda _event: self.window.destroy())
        self.window.bind("<Return>", lambda _event: self.save())
        self.window.update_idletasks()
        x = app.root.winfo_x() + max((app.window_width - self.window.winfo_width()) // 2, 0)
        y = app.root.winfo_y() + app.window_height + app.px(10)
        self.window.geometry(f"+{x}+{y}")
        self.window.focus_force()

    def add_entry(self, row: int, label_key: str, variable: tk.StringVar) -> None:
        tk.Label(
            self.window,
            text=tr(self.language, label_key),
            bg=self.app.theme.background,
            fg=self.app.theme.text_muted,
            font=self.app.ui_font(9),
        ).grid(row=row, column=0, padx=(16, 10), pady=(14, 4), sticky="w")
        tk.Entry(
            self.window,
            textvariable=variable,
            width=30,
            bg=self.app.theme.panel,
            fg=self.app.theme.text_primary,
            insertbackground=self.app.theme.text_primary,
            relief="flat",
            font=self.app.ui_font(10),
        ).grid(row=row, column=1, padx=(0, 16), pady=(14, 4), ipadx=6, ipady=4)

    def save(self) -> None:
        title = self.name_var.get().strip()
        if not title:
            messagebox.showerror(
                tr(self.language, "dialog_title"),
                tr(self.language, "invalid_name"),
                parent=self.window,
            )
            return
        try:
            start = parse_datetime_input(self.start_var.get())
            end = parse_datetime_input(self.end_var.get())
        except ValueError:
            messagebox.showerror(
                tr(self.language, "dialog_title"),
                tr(self.language, "invalid_datetime"),
                parent=self.window,
            )
            return
        if end <= start:
            messagebox.showerror(
                tr(self.language, "dialog_title"),
                tr(self.language, "invalid_range"),
                parent=self.window,
            )
            return
        self.app.save_custom_range(title, start, end, self.custom_id)
        self.window.destroy()


class ProgressBarApp:
    def __init__(self) -> None:
        self.settings = load_settings()
        save_settings(self.settings)
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        dpi = self.root.winfo_fpixels("1i")
        self.ui_scale = min(max(dpi / 96.0, 1.0), 2.5)
        self.logical_width = min(
            max(int(self.settings.get("width", WINDOW_WIDTH)), MIN_WINDOW_WIDTH),
            MAX_WINDOW_WIDTH,
        )
        self.logical_height = min(
            max(int(self.settings.get("height", WINDOW_HEIGHT)), MIN_WINDOW_HEIGHT),
            MAX_WINDOW_HEIGHT,
        )
        self.window_width = self.px(self.logical_width)
        self.window_height = self.px(self.logical_height)
        self.root.tk.call("tk", "scaling", dpi / 72.0)
        self.root.overrideredirect(True)
        self.root.configure(bg=TRANSPARENT_COLOR)
        self.root.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        self.root.wm_attributes("-topmost", bool(self.settings["always_on_top"]))

        x, y = self.initial_position()
        self.root.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")
        self.settings["x"] = x
        self.settings["y"] = y
        save_settings(self.settings)

        self.canvas = tk.Canvas(
            self.root,
            width=self.window_width,
            height=self.window_height,
            bg=TRANSPARENT_COLOR,
            highlightthickness=0,
        )
        self.canvas.pack()

        self.drag_x = 0
        self.drag_y = 0
        self.resize_start_width = 0
        self.resize_start_height = 0
        self.resize_start_x = 0
        self.resize_start_y = 0
        self.is_dragging = False
        self.is_resizing = False
        self.is_visible = True
        self.current_cursor = ""
        self.last_render_key: tuple[Any, ...] | None = None
        self.pending_draw: str | None = None
        self.desktop_mode = False
        self.show_resize_handle = False
        self.tray_icon: NativeTrayIcon | None = None
        self.root.bind("<ButtonPress-1>", self.begin_drag)
        self.root.bind("<B1-Motion>", self.drag)
        self.root.bind("<ButtonRelease-1>", self.end_drag)
        self.root.bind("<Motion>", self.update_cursor)
        self.root.bind("<Leave>", self.hide_resize_handle)
        self.root.bind("<Double-Button-1>", self.cycle_mode)
        self.root.bind("<Button-3>", self.show_menu)

        self.mode_var = tk.StringVar(value=self.settings["mode"])
        self.language_var = tk.StringVar(value=self.settings["language"])
        self.active_custom_var = tk.StringVar(value=self.settings["active_custom_id"])
        selected_theme = self.settings.get("theme", "rainy_night")
        if selected_theme not in THEMES:
            selected_theme = "rainy_night"
        self.theme_scheduler_var = tk.BooleanVar(value=bool(self.settings["theme_scheduler"]))
        if self.theme_scheduler_var.get():
            selected_theme = scheduled_theme_key(datetime.now())
        self.theme_var = tk.StringVar(value=selected_theme)
        self.theme = THEMES[selected_theme]
        self.topmost_var = tk.BooleanVar(value=bool(self.settings["always_on_top"]))
        self.startup_var = tk.BooleanVar(value=is_startup_enabled())
        if self.settings["start_with_windows"] and not self.startup_var.get():
            self.startup_var.set(set_startup_enabled(True))

        self.build_menu()

        self.draw()
        self.root.update_idletasks()
        self.apply_window_layer()
        if sys.platform == "win32":
            try:
                self.tray_icon = NativeTrayIcon(self)
            except (AttributeError, OSError):
                self.tray_icon = None
        self.root.after(250, self.poll_tray_events)
        self.root.after(2_000, self.maintain_window_layer)
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.root.after(1000, self.refresh)

    def build_menu(self) -> None:
        language = self.language_var.get()
        old_menu = getattr(self, "menu", None)
        self.menu = tk.Menu(
            self.root,
            tearoff=False,
            bg=self.theme.panel,
            fg=self.theme.text_primary,
            activebackground=self.theme.track,
            activeforeground=self.theme.text_primary,
            bd=0,
        )
        for mode in ("year", "month", "day"):
            self.menu.add_radiobutton(
                label=tr(language, f"mode_{mode}"),
                value=mode,
                variable=self.mode_var,
                command=self.change_mode,
            )
        self.custom_menu = tk.Menu(self.menu, tearoff=False)
        ranges = self.settings["custom_ranges"]
        if ranges:
            for custom_range in ranges:
                self.custom_menu.add_radiobutton(
                    label=custom_range["title"],
                    value=custom_range["id"],
                    variable=self.active_custom_var,
                    command=self.select_custom_range,
                )
            self.custom_menu.add_separator()
        else:
            self.custom_menu.add_command(
                label=tr(language, "custom_empty"),
                state="disabled",
            )
            self.custom_menu.add_separator()
        self.custom_menu.add_command(
            label=tr(language, "custom_add"),
            command=self.open_custom_range_dialog,
        )
        self.custom_menu.add_command(
            label=tr(language, "custom_edit"),
            command=self.edit_selected_custom_range,
            state="normal" if ranges else "disabled",
        )
        self.custom_menu.add_command(
            label=tr(language, "custom_delete"),
            command=self.delete_selected_custom_range,
            state="normal" if ranges else "disabled",
        )
        self.menu.add_cascade(label=tr(language, "custom_ranges"), menu=self.custom_menu)
        self.menu.add_separator()
        self.theme_menu = tk.Menu(self.menu, tearoff=False)
        self.theme_menu.add_checkbutton(
            label=tr(language, "theme_scheduler"),
            variable=self.theme_scheduler_var,
            command=self.toggle_theme_scheduler,
        )
        self.theme_menu.add_separator()
        for value, theme in THEMES.items():
            self.theme_menu.add_radiobutton(
                label=theme_label(value, language),
                value=value,
                variable=self.theme_var,
                command=self.change_theme,
            )
        self.menu.add_cascade(label=tr(language, "sad_style"), menu=self.theme_menu)
        self.language_menu = tk.Menu(self.menu, tearoff=False)
        for value, label in (("vi", "Tiếng Việt"), ("en", "English"), ("ja", "日本語")):
            self.language_menu.add_radiobutton(
                label=label,
                value=value,
                variable=self.language_var,
                command=self.change_language,
            )
        self.menu.add_cascade(label=tr(language, "language"), menu=self.language_menu)
        self.menu.add_separator()
        self.menu.add_checkbutton(
            label=tr(language, "always_on_top"),
            variable=self.topmost_var,
            command=self.toggle_topmost,
        )
        self.menu.add_checkbutton(
            label=tr(language, "start_with_windows"),
            variable=self.startup_var,
            command=self.toggle_startup,
        )
        self.menu.add_separator()
        self.menu.add_command(label=tr(language, "toggle_widget"), command=self.toggle_visible)
        self.menu.add_command(label=tr(language, "quit"), command=self.shutdown)
        if old_menu is not None:
            old_menu.destroy()

    def px(self, value: int | float) -> int:
        return round(value * self.ui_scale)

    def x(self, value: int | float) -> int:
        return round(value * self.window_width / WINDOW_WIDTH)

    def y(self, value: int | float) -> int:
        return round(value * self.window_height / WINDOW_HEIGHT)

    def radius(self, value: int | float) -> int:
        scale = min(
            self.window_width / self.px(WINDOW_WIDTH),
            self.window_height / self.px(WINDOW_HEIGHT),
        )
        return max(1, round(self.px(value) * scale))

    def font(self, family: str, size: int, *styles: str) -> tuple[Any, ...]:
        scale = min(
            self.logical_width / WINDOW_WIDTH,
            self.logical_height / WINDOW_HEIGHT,
        )
        return (family, max(8, round(size * scale)), *styles)

    def ui_font(self, size: int, *styles: str) -> tuple[Any, ...]:
        family = "Yu Gothic UI" if self.language_var.get() == "ja" else "Segoe UI"
        return self.font(family, size, *styles)

    def initial_position(self) -> tuple[int, int]:
        left, top, screen_width, screen_height = virtual_screen_bounds()
        if not screen_width or not screen_height:
            left, top = 0, 0
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
        x = int(self.settings.get("x", left + screen_width - self.window_width - self.px(34)))
        y = int(self.settings.get("y", top + self.px(42)))
        x = min(max(x, left), max(left + screen_width - self.window_width, left))
        y = min(max(y, top), max(top + screen_height - self.window_height, top))
        return x, y

    def begin_drag(self, event: tk.Event) -> None:
        self.is_resizing = self.in_resize_corner(event.x, event.y)
        self.is_dragging = not self.is_resizing
        if self.is_resizing:
            self.resize_start_width = self.window_width
            self.resize_start_height = self.window_height
            self.resize_start_x = event.x_root
            self.resize_start_y = event.y_root
            return
        self.drag_x = event.x_root
        self.drag_y = event.y_root
        self.drag_window_x, self.drag_window_y = self.screen_position()

    def drag(self, event: tk.Event) -> None:
        if self.is_resizing:
            self.resize(event.x_root, event.y_root)
            return
        x = self.drag_window_x + event.x_root - self.drag_x
        y = self.drag_window_y + event.y_root - self.drag_y
        self.set_screen_position(x, y)

    def end_drag(self, _event: tk.Event) -> None:
        self.settings["x"], self.settings["y"] = self.screen_position()
        self.settings["width"] = self.logical_width
        self.settings["height"] = self.logical_height
        save_settings(self.settings)
        self.is_dragging = False
        self.is_resizing = False

    def in_resize_corner(self, x: int, y: int) -> bool:
        size = self.px(26)
        return x >= self.window_width - size and y >= self.window_height - size

    def update_cursor(self, event: tk.Event) -> None:
        show_handle = self.in_resize_corner(event.x, event.y)
        cursor = "size_nw_se" if show_handle else "arrow"
        if cursor != self.current_cursor:
            self.root.configure(cursor=cursor)
            self.current_cursor = cursor
        if show_handle != self.show_resize_handle:
            self.show_resize_handle = show_handle
            self.request_draw()

    def hide_resize_handle(self, _event: tk.Event) -> None:
        if self.show_resize_handle and not self.is_resizing:
            self.show_resize_handle = False
            self.request_draw()

    def resize(self, x_root: int, y_root: int) -> None:
        width = self.resize_start_width + x_root - self.resize_start_x
        height = self.resize_start_height + y_root - self.resize_start_y
        logical_width = round(width / self.ui_scale)
        logical_height = round(height / self.ui_scale)
        self.logical_width = min(max(logical_width, MIN_WINDOW_WIDTH), MAX_WINDOW_WIDTH)
        self.logical_height = min(max(logical_height, MIN_WINDOW_HEIGHT), MAX_WINDOW_HEIGHT)
        self.window_width = self.px(self.logical_width)
        self.window_height = self.px(self.logical_height)
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        self.canvas.configure(width=self.window_width, height=self.window_height)
        self.request_draw()

    def show_menu(self, event: tk.Event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def show_tray_menu(self) -> None:
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        try:
            self.menu.tk_popup(x, y)
        finally:
            self.menu.grab_release()

    def poll_tray_events(self) -> None:
        if self.tray_icon is None:
            return
        while True:
            try:
                event = self.tray_icon.events.get_nowait()
            except queue.Empty:
                break
            if event == "show":
                self.show_widget()
            elif event == "menu":
                self.show_tray_menu()
        self.root.after(250, self.poll_tray_events)

    def toggle_visible(self) -> None:
        if self.is_visible:
            self.hide_widget()
        else:
            self.show_widget()

    def hide_widget(self) -> None:
        if self.is_visible:
            self.root.withdraw()
            self.is_visible = False

    def show_widget(self) -> None:
        self.keep_on_screen()
        self.root.deiconify()
        self.apply_window_layer()
        if self.topmost_var.get():
            self.root.lift()
        self.is_visible = True
        self.draw(force=True)

    def keep_on_screen(self) -> None:
        left, top, screen_width, screen_height = virtual_screen_bounds()
        if not screen_width or not screen_height:
            left, top = 0, 0
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
        current_x, current_y = self.screen_position()
        x = min(max(current_x, left), max(left + screen_width - self.window_width, left))
        y = min(max(current_y, top), max(top + screen_height - self.window_height, top))
        self.set_screen_position(x, y)

    def window_handle(self) -> int:
        child_handle = self.root.winfo_id()
        if sys.platform != "win32":
            return child_handle
        user32 = ctypes.windll.user32
        user32.GetAncestor.restype = wintypes.HWND
        return user32.GetAncestor(child_handle, GA_ROOT) or child_handle

    def screen_position(self) -> tuple[int, int]:
        if sys.platform != "win32":
            return self.root.winfo_x(), self.root.winfo_y()
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(self.window_handle(), ctypes.byref(rect))
        return rect.left, rect.top

    def set_screen_position(self, x: int, y: int) -> None:
        if sys.platform != "win32":
            self.root.geometry(f"+{x}+{y}")
            return
        user32 = ctypes.windll.user32
        user32.SetWindowPos(
            self.window_handle(),
            None,
            x,
            y,
            0,
            0,
            SWP_NOSIZE | SWP_NOACTIVATE,
        )

    def update_surface(self) -> None:
        color = TRANSPARENT_COLOR
        self.root.configure(bg=color)
        self.canvas.configure(bg=color)

    def apply_window_layer(self) -> None:
        if self.topmost_var.get():
            self.leave_desktop_mode()
            self.root.wm_attributes("-topmost", True)
        else:
            self.root.wm_attributes("-topmost", False)
            self.enter_desktop_mode()

    def maintain_window_layer(self) -> None:
        if (
            self.is_visible
            and self.desktop_mode
            and not self.is_dragging
            and not self.is_resizing
            and sys.platform == "win32"
        ):
            ctypes.windll.user32.SetWindowPos(
                self.window_handle(),
                HWND_BOTTOM,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )
        self.root.after(2_000, self.maintain_window_layer)

    def enter_desktop_mode(self) -> None:
        if sys.platform != "win32":
            return
        hwnd = self.window_handle()
        user32 = ctypes.windll.user32
        self.desktop_mode = True
        self.update_surface()
        user32.SetWindowPos(
            hwnd,
            HWND_BOTTOM,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        )
        self.draw(force=True)

    def leave_desktop_mode(self) -> None:
        self.desktop_mode = False
        self.update_surface()
        self.keep_on_screen()
        self.draw(force=True)

    def shutdown(self) -> None:
        if self.tray_icon is not None:
            self.tray_icon.remove()
            self.tray_icon = None
        self.root.destroy()

    def cycle_mode(self, _event: tk.Event) -> None:
        modes = ["year", "month", "day"]
        if self.settings["custom_ranges"]:
            modes.append("custom")
        current = modes.index(self.mode_var.get())
        self.mode_var.set(modes[(current + 1) % len(modes)])
        self.change_mode()

    def change_mode(self) -> None:
        self.settings["mode"] = self.mode_var.get()
        save_settings(self.settings)
        self.draw(force=True)

    def open_custom_range_dialog(self) -> None:
        CustomRangeDialog(self)

    def selected_custom_range(self) -> dict[str, str] | None:
        selected_id = self.active_custom_var.get()
        for custom_range in self.settings["custom_ranges"]:
            if custom_range["id"] == selected_id:
                return custom_range
        return None

    def select_custom_range(self) -> None:
        self.settings["active_custom_id"] = self.active_custom_var.get()
        self.settings["mode"] = "custom"
        self.mode_var.set("custom")
        save_settings(self.settings)
        self.draw(force=True)

    def save_custom_range(
        self,
        title: str,
        start: datetime,
        end: datetime,
        custom_id: str | None = None,
    ) -> None:
        saved_range = {
            "id": custom_id or uuid.uuid4().hex[:12],
            "title": title,
            "start": start.isoformat(timespec="minutes"),
            "end": end.isoformat(timespec="minutes"),
        }
        ranges = self.settings["custom_ranges"]
        for index, custom_range in enumerate(ranges):
            if custom_range["id"] == saved_range["id"]:
                ranges[index] = saved_range
                break
        else:
            ranges.append(saved_range)
        self.settings["active_custom_id"] = saved_range["id"]
        self.active_custom_var.set(saved_range["id"])
        self.settings["mode"] = "custom"
        self.mode_var.set("custom")
        save_settings(self.settings)
        self.build_menu()
        self.draw(force=True)

    def edit_selected_custom_range(self) -> None:
        custom_range = self.selected_custom_range()
        if custom_range is not None:
            CustomRangeDialog(self, custom_range)

    def delete_selected_custom_range(self) -> None:
        custom_range = self.selected_custom_range()
        if custom_range is None:
            return
        language = self.language_var.get()
        confirmed = messagebox.askyesno(
            tr(language, "delete_title"),
            tr(language, "delete_confirm", name=custom_range["title"]),
            parent=self.root,
        )
        if not confirmed:
            return
        ranges = self.settings["custom_ranges"]
        ranges[:] = [item for item in ranges if item["id"] != custom_range["id"]]
        next_range = ranges[0] if ranges else None
        next_id = next_range["id"] if next_range else ""
        self.settings["active_custom_id"] = next_id
        self.active_custom_var.set(next_id)
        if not next_range and self.mode_var.get() == "custom":
            self.settings["mode"] = "day"
            self.mode_var.set("day")
        save_settings(self.settings)
        self.build_menu()
        self.draw(force=True)

    def change_language(self) -> None:
        self.settings["language"] = self.language_var.get()
        save_settings(self.settings)
        self.build_menu()
        self.draw(force=True)

    def change_theme(self) -> None:
        if self.theme_scheduler_var.get():
            self.theme_scheduler_var.set(False)
            self.settings["theme_scheduler"] = False
        self.settings["theme"] = self.theme_var.get()
        self.theme = THEMES[self.theme_var.get()]
        save_settings(self.settings)
        self.build_menu()
        self.update_surface()
        self.draw(force=True)

    def toggle_theme_scheduler(self) -> None:
        enabled = self.theme_scheduler_var.get()
        self.settings["theme_scheduler"] = enabled
        if enabled:
            self.apply_scheduled_theme()
        else:
            theme_key = self.settings["theme"]
            self.theme_var.set(theme_key)
            self.theme = THEMES[theme_key]
        save_settings(self.settings)
        self.build_menu()
        self.update_surface()
        self.draw(force=True)

    def apply_scheduled_theme(self) -> None:
        if not self.theme_scheduler_var.get():
            return
        theme_key = scheduled_theme_key(datetime.now())
        if theme_key == self.theme_var.get():
            return
        self.theme_var.set(theme_key)
        self.theme = THEMES[theme_key]
        self.build_menu()
        self.update_surface()
        self.draw(force=True)

    def toggle_topmost(self) -> None:
        enabled = self.topmost_var.get()
        self.settings["always_on_top"] = enabled
        self.apply_window_layer()
        save_settings(self.settings)

    def toggle_startup(self) -> None:
        enabled = set_startup_enabled(self.startup_var.get())
        self.startup_var.set(enabled)
        self.settings["start_with_windows"] = enabled
        save_settings(self.settings)

    def rounded_rectangle(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        radius: int,
        **kwargs: Any,
    ) -> int:
        x1, y1, x2, y2, radius = (
            self.x(x1),
            self.y(y1),
            self.x(x2),
            self.y(y2),
            self.radius(radius),
        )
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def draw_progress(self, x1: int, y1: int, x2: int, y2: int, ratio: float) -> None:
        theme = self.theme
        radius = (y2 - y1) // 2
        self.rounded_rectangle(x1, y1, x2, y2, radius, fill=theme.track, outline="")
        fill_width = max(0, round((x2 - x1) * ratio))
        if fill_width <= 0:
            return

        fill_x2 = min(x1 + fill_width, x2)
        self.rounded_rectangle(
            x1,
            y1,
            max(fill_x2, x1 + radius * 2),
            y2,
            radius,
            fill=theme.accent_start,
            outline="",
        )
        segment_count = min(GRADIENT_SEGMENTS, max(fill_width, 1))
        for index in range(segment_count):
            start_x = x1 + fill_width * index / segment_count
            end_x = x1 + fill_width * (index + 1) / segment_count
            color_ratio = index / max(segment_count - 1, 1)
            color = blend_color(theme.accent_start, theme.accent_end, color_ratio)
            self.canvas.create_rectangle(
                self.x(start_x),
                self.y(y1 + 2),
                self.x(end_x) + 1,
                self.y(y2 - 2),
                fill=color,
                outline="",
            )

        if fill_width < radius * 2:
            self.canvas.create_oval(
                self.x(x1),
                self.y(y1),
                self.x(x1 + radius * 2),
                self.y(y2),
                fill=theme.accent_start,
                outline="",
            )

    def request_draw(self) -> None:
        if self.pending_draw is not None:
            return
        self.pending_draw = self.root.after(16, self.draw)

    def draw(self, force: bool = False) -> None:
        self.pending_draw = None
        language = self.language_var.get()
        progress = calculate_progress(
            datetime.now(),
            self.mode_var.get(),
            language,
            self.settings,
        )
        theme = self.theme
        render_key = (
            self.mode_var.get(),
            language,
            self.theme_var.get(),
            self.desktop_mode,
            self.show_resize_handle,
            self.window_width,
            self.window_height,
            progress.title,
            progress.detail,
            f"{progress.ratio * 100:05.2f}",
        )
        if not force and render_key == self.last_render_key:
            return
        self.last_render_key = render_key
        self.canvas.delete("all")

        self.rounded_rectangle(
            4,
            4,
            WINDOW_WIDTH - 4,
            WINDOW_HEIGHT - 4,
            22,
            fill=theme.background,
            outline=theme.border,
            width=max(1, self.radius(1)),
        )
        self.rounded_rectangle(
            14,
            14,
            WINDOW_WIDTH - 14,
            WINDOW_HEIGHT - 14,
            16,
            fill=theme.panel,
            outline="",
        )
        self.canvas.create_text(
            self.x(29),
            self.y(29),
            text=progress.title,
            anchor="w",
            fill=theme.text_muted,
            font=self.ui_font(10, "bold"),
        )
        self.canvas.create_text(
            self.x(WINDOW_WIDTH - 28),
            self.y(37),
            text=f"{progress.ratio * 100:05.2f}%",
            anchor="e",
            fill=theme.text_primary,
            font=self.font("Segoe UI Semibold", 21),
        )
        self.draw_progress(29, 63, WINDOW_WIDTH - 29, 78, progress.ratio)
        self.canvas.create_text(
            self.x(29),
            self.y(98),
            text=progress.detail,
            anchor="w",
            fill=theme.text_muted,
            font=self.ui_font(9),
        )
        self.canvas.create_text(
            self.x(29),
            self.y(126),
            text=theme_quote(self.theme_var.get(), language),
            anchor="w",
            fill=theme.text_faint,
            font=self.ui_font(9, "italic"),
        )
        if self.show_resize_handle or self.is_resizing:
            handle_x = WINDOW_WIDTH - 17
            handle_y = WINDOW_HEIGHT - 16
            for offset in (0, 5):
                self.canvas.create_line(
                    self.x(handle_x + offset),
                    self.y(WINDOW_HEIGHT - 7),
                    self.x(WINDOW_WIDTH - 7),
                    self.y(handle_y + offset),
                    fill=theme.text_faint,
                    width=max(1, self.radius(1)),
                )

    def refresh(self) -> None:
        self.apply_scheduled_theme()
        if self.is_visible:
            self.draw()
        interval = REFRESH_INTERVALS.get(self.mode_var.get(), 30_000)
        self.root.after(interval, self.refresh)

    def run(self) -> None:
        self.root.mainloop()


def run_check() -> None:
    now = datetime.now()
    checks = {mode: calculate_progress(now, mode).__dict__ for mode in ("year", "month", "day")}
    checks["calendar_days_this_month"] = calendar.monthrange(now.year, now.month)[1]
    checks["themes"] = [theme.label for theme in THEMES.values()]
    checks["startup_command"] = startup_command()
    print(json.dumps(checks, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Print calculated progress without opening the widget.",
    )
    args = parser.parse_args()
    if args.check:
        run_check()
        return
    if not claim_single_instance():
        return
    enable_high_dpi()
    ProgressBarApp().run()


if __name__ == "__main__":
    main()
