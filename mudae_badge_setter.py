import ctypes
import json
import os
import shutil
import sys
import threading
import time
import tkinter as tk
from ctypes import wintypes
from pathlib import Path
from tkinter import ttk

from mudae_logic import (
    BADGES,
    BADGE_DATA_FILENAME,
    DEFAULT_DELAY,
    badge_level_cost,
    badge_info_lines,
    badge_prerequisite_status,
    build_command_sequence,
    clear_locked_badges,
    configuration_prerequisite_errors,
    find_matching_config_name,
    format_kakera,
    format_set_result_message,
    load_badge_data,
    next_level_kakera_cost,
    normalize_badge_data,
    normalize_badge_counts,
    seed_default_configurations,
    total_kakera_cost,
    validate_delay,
    validate_user_id,
)


APP_DATA_FOLDER = "Mudae Badge Setter"
CONFIG_FILENAME = "configs.json"
SETTINGS_FILENAME = "settings.json"
LEGACY_CONFIG_FILENAME = "mudae_kakera_configs.json"
LEGACY_SETTINGS_FILENAME = "mudae_kakera_last_state.json"


def app_base_dir(is_frozen=None, executable=None, source_file=None):
    if is_frozen is None:
        is_frozen = getattr(sys, "frozen", False)
    if is_frozen:
        return Path(executable or sys.executable).resolve().parent
    return Path(source_file or __file__).resolve().parent


def app_data_dir(appdata=None, home=None):
    if appdata is None:
        appdata = os.environ.get("APPDATA", "")
    if appdata:
        return Path(appdata) / APP_DATA_FOLDER
    return Path(home or Path.home()) / "AppData" / "Roaming" / APP_DATA_FOLDER


def runtime_file_path(filename, appdata=None, home=None):
    return app_data_dir(appdata, home) / filename


def legacy_runtime_file_paths(filename, is_frozen=None, executable=None, source_file=None):
    paths = [app_base_dir(is_frozen, executable, source_file) / filename]
    source_path = Path(source_file or __file__).resolve().parent / filename
    if source_path not in paths:
        paths.append(source_path)
    return paths


def migrate_runtime_file(target_path, legacy_paths):
    target_path = Path(target_path)
    if target_path.exists():
        return False
    for legacy_path in legacy_paths:
        legacy_path = Path(legacy_path)
        if legacy_path.exists():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(legacy_path), str(target_path))
            return True
    return False


def cleanup_obsolete_runtime_files(paths):
    removed = 0
    for path in paths:
        path = Path(path)
        try:
            if path.exists():
                path.unlink()
                removed += 1
        except OSError:
            pass
    return removed


def migrate_runtime_files():
    migrate_runtime_file(
        CONFIG_PATH,
        [runtime_file_path(LEGACY_CONFIG_FILENAME)]
        + legacy_runtime_file_paths(CONFIG_FILENAME)
        + legacy_runtime_file_paths(LEGACY_CONFIG_FILENAME),
    )
    migrate_runtime_file(
        SETTINGS_PATH,
        [runtime_file_path(LEGACY_SETTINGS_FILENAME)]
        + legacy_runtime_file_paths(SETTINGS_FILENAME)
        + legacy_runtime_file_paths(LEGACY_SETTINGS_FILENAME),
    )
    cleanup_obsolete_runtime_files(
        [
            runtime_file_path(LEGACY_CONFIG_FILENAME),
            runtime_file_path(LEGACY_SETTINGS_FILENAME),
        ]
    )


CONFIG_PATH = runtime_file_path(CONFIG_FILENAME)
SETTINGS_PATH = runtime_file_path(SETTINGS_FILENAME)
BADGE_DATA_PATH = runtime_file_path(BADGE_DATA_FILENAME)
APP_TITLE = "Mudae Badge Setter"
POINTS_PER_INCH = 72.0
WINDOW_WIDTH_SCREEN_FRACTION = 0.35
WINDOW_HEIGHT_SCREEN_FRACTION = 0.40
HELP_POPUP_WIDTH_FRACTION = 0.30
POPUP_HORIZONTAL_PADDING = 32
BADGE_LEVELS = ((1, "I"), (2, "II"), (3, "III"), (4, "IV"))
HELP_LINES = (
    "How to use this app:",
    "",
    "1. Open Discord desktop to the text channel where Mudae should receive commands.",
    "2. Enter your discord userID.",
    "3. Set the Message delay. Use a larger value if Discord misses messages.",
    "4. Set badge counts from 0 to 4.",
    "5. Locked badges stay at 0 until their prerequisites are met.",
    "6. Check the total cost and each badge's next-level cost.",
    "7. Click Edit Badge Cost to change badge prices.",
    "8. Click a badge name to view its costs, prerequisites, and perks.",
    "9. Click New to clear the name and badge counts for a fresh configuration.",
    "10. Enter a configuration name and click Save / Update to save the current badge counts.",
    "11. Click a saved configuration to load it into the fields.",
    "12. Use Delete to remove the selected or named configuration.",
    "13. Click Set to run the sequence.",
    "",
    "When Set runs, the app briefly focuses Discord, clicks the current channel message box, sends the refund/confirm commands, sends the badge commands, then returns focus to this window.",
)
USER_ID_HELP_TEXT = """How to get your Discord user ID:

- Click the gear icon (Settings) in the bottom left corner next to your username.
- Scroll down to the App Settings section and click Advanced.
- Toggle the Developer Mode switch to the ON position.
- Desktop: Click your profile picture at the bottom left, click the three dots (...), and choose Copy ID."""


def enable_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def configure_tk_scaling(root):
    try:
        pixels_per_inch = root.winfo_fpixels("1i")
    except tk.TclError:
        return
    if pixels_per_inch > 0:
        root.tk.call("tk", "scaling", pixels_per_inch / POINTS_PER_INCH)


def screen_fraction_geometry(
    screen_width,
    screen_height,
    width_fraction=WINDOW_WIDTH_SCREEN_FRACTION,
    height_fraction=WINDOW_HEIGHT_SCREEN_FRACTION,
):
    width = max(1, int(screen_width * width_fraction))
    height = max(1, int(screen_height * height_fraction))
    return f"{width}x{height}"


def popup_window_width(window_width, fraction=HELP_POPUP_WIDTH_FRACTION):
    return max(1, int(window_width * fraction))


def popup_wraplength(window_width, fraction=HELP_POPUP_WIDTH_FRACTION):
    return max(1, popup_window_width(window_width, fraction) - POPUP_HORIZONTAL_PADDING)


def empty_badge_counts():
    return {badge: 0 for badge in BADGES}


class WindowsClipboard:
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    def __init__(self):
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        self.user32.OpenClipboard.argtypes = [wintypes.HWND]
        self.user32.OpenClipboard.restype = wintypes.BOOL
        self.user32.CloseClipboard.argtypes = []
        self.user32.CloseClipboard.restype = wintypes.BOOL
        self.user32.EmptyClipboard.argtypes = []
        self.user32.EmptyClipboard.restype = wintypes.BOOL
        self.user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
        self.user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
        self.user32.GetClipboardData.argtypes = [wintypes.UINT]
        self.user32.GetClipboardData.restype = wintypes.HANDLE
        self.user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        self.user32.SetClipboardData.restype = wintypes.HANDLE

        self.kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        self.kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
        self.kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        self.kernel32.GlobalLock.restype = ctypes.c_void_p
        self.kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        self.kernel32.GlobalUnlock.restype = wintypes.BOOL
        self.kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
        self.kernel32.GlobalFree.restype = wintypes.HGLOBAL

    def get_text(self):
        if not self.user32.IsClipboardFormatAvailable(self.CF_UNICODETEXT):
            return None
        if not self.user32.OpenClipboard(None):
            return None
        handle = None
        pointer = None
        try:
            handle = self.user32.GetClipboardData(self.CF_UNICODETEXT)
            if not handle:
                return None
            pointer = self.kernel32.GlobalLock(handle)
            if not pointer:
                return None
            return ctypes.wstring_at(pointer)
        finally:
            if handle and pointer:
                self.kernel32.GlobalUnlock(handle)
            self.user32.CloseClipboard()

    def set_text(self, text):
        if not self.user32.OpenClipboard(None):
            raise RuntimeError("Could not open the Windows clipboard.")
        data_handle = None
        try:
            if not self.user32.EmptyClipboard():
                raise RuntimeError("Could not clear the Windows clipboard.")

            size = (len(text) + 1) * ctypes.sizeof(ctypes.c_wchar)
            data_handle = self.kernel32.GlobalAlloc(self.GMEM_MOVEABLE, size)
            if not data_handle:
                raise RuntimeError("Could not allocate clipboard memory.")

            pointer = self.kernel32.GlobalLock(data_handle)
            if not pointer:
                raise RuntimeError("Could not lock clipboard memory.")
            try:
                ctypes.memmove(pointer, ctypes.create_unicode_buffer(text), size)
            finally:
                self.kernel32.GlobalUnlock(data_handle)

            if not self.user32.SetClipboardData(self.CF_UNICODETEXT, data_handle):
                raise RuntimeError("Could not write to the Windows clipboard.")
            data_handle = None
        finally:
            if data_handle:
                self.kernel32.GlobalFree(data_handle)
            self.user32.CloseClipboard()


class DiscordSender:
    SW_RESTORE = 9
    KEYEVENTF_KEYUP = 0x0002
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    VK_CONTROL = 0x11
    VK_V = 0x56
    VK_RETURN = 0x0D
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def __init__(self, delay):
        self.delay = delay
        self.clipboard = WindowsClipboard()
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._configure_user32()

    def _configure_user32(self):
        self.user32.EnumWindows.argtypes = [self.WNDENUMPROC, wintypes.LPARAM]
        self.user32.EnumWindows.restype = wintypes.BOOL
        self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user32.IsWindowVisible.restype = wintypes.BOOL
        self.user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self.user32.GetWindowTextLengthW.restype = ctypes.c_int
        self.user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetWindowTextW.restype = ctypes.c_int
        self.user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.ShowWindow.restype = wintypes.BOOL
        self.user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        self.user32.SetForegroundWindow.restype = wintypes.BOOL
        self.user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user32.GetWindowRect.restype = wintypes.BOOL
        self.user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
        self.user32.SetCursorPos.restype = wintypes.BOOL
        self.user32.mouse_event.argtypes = [
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
        ]
        self.user32.mouse_event.restype = None
        self.user32.keybd_event.argtypes = [
            wintypes.BYTE,
            wintypes.BYTE,
            wintypes.DWORD,
            ctypes.c_void_p,
        ]
        self.user32.keybd_event.restype = None

    def find_discord_window(self):
        matches = []

        def callback(hwnd, _lparam):
            if not self.user32.IsWindowVisible(hwnd):
                return True
            length = self.user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            self.user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value
            if "discord" in title.lower():
                matches.append((hwnd, title))
            return True

        enum_proc = self.WNDENUMPROC(callback)
        self.user32.EnumWindows(enum_proc, 0)
        if not matches:
            raise RuntimeError("Could not find an open Discord window.")
        return matches[0][0]

    def focus_discord(self, hwnd):
        self.user32.ShowWindow(hwnd, self.SW_RESTORE)
        time.sleep(0.2)
        self.user32.SetForegroundWindow(hwnd)
        time.sleep(0.4)

    def click_message_box(self, hwnd):
        rect = wintypes.RECT()
        if not self.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise RuntimeError("Could not read the Discord window position.")
        x = int((rect.left + rect.right) / 2)
        y = int(rect.bottom - 48)
        self.user32.SetCursorPos(x, y)
        time.sleep(0.1)
        self.user32.mouse_event(self.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, None)
        time.sleep(0.05)
        self.user32.mouse_event(self.MOUSEEVENTF_LEFTUP, 0, 0, 0, None)
        time.sleep(0.25)

    def _key_down(self, key):
        self.user32.keybd_event(key, 0, 0, None)

    def _key_up(self, key):
        self.user32.keybd_event(key, 0, self.KEYEVENTF_KEYUP, None)

    def _press_key(self, key):
        self._key_down(key)
        time.sleep(0.03)
        self._key_up(key)

    def _paste_clipboard(self):
        self._key_down(self.VK_CONTROL)
        time.sleep(0.03)
        self._press_key(self.VK_V)
        time.sleep(0.03)
        self._key_up(self.VK_CONTROL)

    def send_message(self, message):
        self.clipboard.set_text(message)
        time.sleep(0.05)
        self._paste_clipboard()
        time.sleep(0.05)
        self._press_key(self.VK_RETURN)

    def send_messages(self, messages):
        discord_hwnd = self.find_discord_window()
        original_clipboard = self.clipboard.get_text()
        try:
            self.focus_discord(discord_hwnd)
            self.click_message_box(discord_hwnd)
            for index, message in enumerate(messages):
                self.send_message(message)
                if index < len(messages) - 1:
                    time.sleep(self.delay)
        finally:
            if original_clipboard is not None:
                self.clipboard.set_text(original_clipboard)


class ConfigStore:
    def __init__(self, path):
        self.path = path

    @staticmethod
    def _normalize_entry(config):
        config = config if isinstance(config, dict) else {}
        raw_badges = config.get("badges", config)
        return {"badges": normalize_badge_counts(raw_badges if isinstance(raw_badges, dict) else {})}

    def load(self):
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(name): self._normalize_entry(config) for name, config in data.items()}

    def save(self, configs):
        normalized = {str(name): self._normalize_entry(config) for name, config in configs.items()}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(normalized, file, indent=2, sort_keys=True)


class BadgeDataStore:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        badge_data = load_badge_data(self.path)
        self.save(badge_data)
        return badge_data

    def save(self, badge_data):
        normalized = normalize_badge_data(badge_data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(normalized, file, indent=2, sort_keys=True)


class SilentPopup:
    def __init__(self, parent, title, lines=None, wrap_source=None):
        self.parent = parent
        self.wrap_source = wrap_source or parent
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.transient(parent)
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.frame = ttk.Frame(self.window, padding=16)
        self.frame.grid(row=0, column=0, sticky="nsew")
        self.frame.columnconfigure(0, weight=1)
        self._row = 0
        if lines:
            self.add_lines(lines)

    def add_lines(self, lines):
        for line in lines:
            self.add_line(line)

    def add_line(self, text):
        ttk.Label(self.frame, text=text, wraplength=self._wraplength(), justify="left").grid(
            row=self._row,
            column=0,
            sticky="w",
            pady=(0, 4),
        )
        self._row += 1

    def _wraplength(self):
        return popup_wraplength(self._source_width())

    def _target_width(self):
        return popup_window_width(self._source_width())

    def _source_width(self):
        try:
            self.wrap_source.update_idletasks()
            width = self.wrap_source.winfo_width()
        except tk.TclError:
            width = 1
        return width

    def add_help_line_with_user_id_link(self, command):
        row_frame = ttk.Frame(self.frame)
        row_frame.grid(row=self._row, column=0, sticky="w", pady=(0, 4))
        ttk.Label(row_frame, text="2. Enter your discord ").grid(row=0, column=0, sticky="w")
        link = tk.Label(
            row_frame,
            text="userID",
            fg="#0645ad",
            cursor="hand2",
            font=("TkDefaultFont", 9, "underline"),
        )
        link.grid(row=0, column=1, sticky="w")
        link.bind("<Button-1>", lambda _event: command())
        ttk.Label(row_frame, text=".").grid(row=0, column=2, sticky="w")
        self._row += 1

    def add_button_row(self):
        button_frame = ttk.Frame(self.frame)
        button_frame.grid(row=self._row, column=0, sticky="e", pady=(10, 0))
        ttk.Button(button_frame, text="OK", command=self.close).grid(row=0, column=0)
        self._row += 1

    def show(self):
        self.add_button_row()
        self.window.update_idletasks()
        self._center()
        self.window.grab_set()
        self.window.focus_force()

    def _center(self):
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        width = self._target_width()
        height = self.window.winfo_height()
        x = parent_x + max(0, int((parent_width - width) / 2))
        y = parent_y + max(0, int((parent_height - height) / 2))
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def close(self):
        self.window.grab_release()
        self.window.destroy()


class BadgeCostEditor:
    def __init__(self, parent, badge_data, save_command):
        self.parent = parent
        self.badge_data = normalize_badge_data(badge_data)
        self.save_command = save_command
        self.cost_vars = {}
        self.error_var = tk.StringVar()
        self.window = tk.Toplevel(parent)
        self.window.title(f"{APP_TITLE} - Edit Badge Cost")
        self.window.transient(parent)
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.frame = ttk.Frame(self.window, padding=16)
        self.frame.grid(row=0, column=0, sticky="nsew")
        self._build()

    def _build(self):
        ttk.Label(self.frame, text="Badge").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 8))
        for column, (_level, label) in enumerate(BADGE_LEVELS, start=1):
            ttk.Label(self.frame, text=f"Level {label}").grid(
                row=0,
                column=column,
                sticky="ew",
                padx=4,
                pady=(0, 8),
            )

        for row, badge in enumerate(BADGES, start=1):
            ttk.Label(self.frame, text=badge.title()).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=3)
            for column, (level, _label) in enumerate(BADGE_LEVELS, start=1):
                var = tk.StringVar(value=str(badge_level_cost(badge, level, self.badge_data)))
                self.cost_vars[(badge, level)] = var
                ttk.Entry(self.frame, textvariable=var, width=11, justify="right").grid(
                    row=row,
                    column=column,
                    sticky="ew",
                    padx=4,
                    pady=3,
                )

        error_label = tk.Label(self.frame, textvariable=self.error_var, fg="#9b1c1c", anchor="w")
        error_label.grid(row=len(BADGES) + 1, column=0, columnspan=5, sticky="ew", pady=(10, 0))

        button_frame = ttk.Frame(self.frame)
        button_frame.grid(row=len(BADGES) + 2, column=0, columnspan=5, sticky="e", pady=(12, 0))
        ttk.Button(button_frame, text="Save", command=self.save).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(button_frame, text="Cancel", command=self.close).grid(row=0, column=1)

    def _collect_badge_data(self):
        badge_data = normalize_badge_data(self.badge_data)
        for badge in BADGES:
            for level, label in BADGE_LEVELS:
                raw_cost = self.cost_vars[(badge, level)].get().strip().replace(",", "")
                try:
                    cost = int(raw_cost)
                except ValueError as exc:
                    raise ValueError(f"{badge.title()} Level {label} cost must be a whole number.") from exc
                if cost < 0:
                    raise ValueError(f"{badge.title()} Level {label} cost cannot be negative.")
                badge_data["badges"][badge]["costs"][str(level)] = cost
        return badge_data

    def save(self):
        try:
            badge_data = self._collect_badge_data()
            self.save_command(badge_data)
        except (OSError, ValueError) as exc:
            self.error_var.set(str(exc))
            return
        self.close()

    def show(self):
        self.window.update_idletasks()
        self._center()
        self.window.grab_set()
        self.window.focus_force()

    def _center(self):
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = parent_x + max(0, int((parent_width - width) / 2))
        y = parent_y + max(0, int((parent_height - height) / 2))
        self.window.geometry(f"+{x}+{y}")

    def close(self):
        self.window.grab_release()
        self.window.destroy()


class SettingsStore:
    def __init__(self, path):
        self.path = path

    def load(self):
        if not self.path.exists():
            return self._normalize({})
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return self._normalize({})
        return self._normalize(data)

    def save(self, state):
        normalized = self._normalize(state)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(normalized, file, indent=2, sort_keys=True)

    @staticmethod
    def _normalize(state):
        state = state if isinstance(state, dict) else {}
        try:
            delay = validate_delay(str(state.get("delay", DEFAULT_DELAY)))
        except ValueError:
            delay = DEFAULT_DELAY
        return {
            "user_id": str(state.get("user_id", "")).strip(),
            "delay": delay,
        }


class KakeraSetterApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(
            screen_fraction_geometry(self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        )
        self.root.minsize(360, 300)

        migrate_runtime_files()
        self.badge_data_store = BadgeDataStore(BADGE_DATA_PATH)
        self.badge_data = self.badge_data_store.load()
        self.store = ConfigStore(CONFIG_PATH)
        self.settings_store = SettingsStore(SETTINGS_PATH)
        self.configs = seed_default_configurations(self.store.load(), self.badge_data)
        self.store.save(self.configs)
        self.badge_vars = {}
        self.badge_spinboxes = {}
        self.badge_next_cost_vars = {}
        self.is_sending = False
        self.is_updating_badge_ui = False

        self.user_id_var = tk.StringVar()
        self.delay_var = tk.StringVar(value=str(DEFAULT_DELAY))
        self.config_name_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.total_cost_var = tk.StringVar(value="Total cost: 0 kakera")

        self._build_ui()
        self._load_settings()
        self._refresh_config_list()
        self._update_badge_ui_state()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=14)
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(4, weight=1)

        ttk.Label(main, text="Discord user ID").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Entry(main, textvariable=self.user_id_var).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(main, text="Message delay").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Entry(main, textvariable=self.delay_var, width=10).grid(row=1, column=1, sticky="w", pady=4)

        badge_frame = ttk.LabelFrame(main, text="Badges", padding=10)
        badge_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 8))
        for index, badge in enumerate(BADGES):
            badge_frame.columnconfigure(index, weight=1)
            badge_label = tk.Label(
                badge_frame,
                text=badge.title(),
                fg="#0645ad",
                cursor="hand2",
                font=("TkDefaultFont", 9, "underline"),
            )
            badge_label.grid(row=0, column=index, padx=4, pady=(0, 4))
            badge_label.bind("<Button-1>", lambda _event, badge=badge: self.show_badge_info(badge))
            var = tk.StringVar(value="0")
            self.badge_vars[badge] = var
            spinbox = tk.Spinbox(
                badge_frame,
                from_=0,
                to=4,
                width=4,
                textvariable=var,
                justify="center",
                wrap=False,
                command=self._update_badge_ui_state,
            )
            spinbox.grid(row=1, column=index, padx=4)
            self.badge_spinboxes[badge] = spinbox
            self.badge_next_cost_vars[badge] = tk.StringVar()
            ttk.Label(
                badge_frame,
                textvariable=self.badge_next_cost_vars[badge],
                anchor="center",
                justify="center",
                width=11,
            ).grid(row=2, column=index, padx=2, pady=(4, 0))
            var.trace_add("write", lambda *_args: self._update_badge_ui_state())

        ttk.Label(badge_frame, textvariable=self.total_cost_var).grid(
            row=3,
            column=0,
            columnspan=len(BADGES),
            sticky="w",
            pady=(10, 0),
        )

        config_frame = ttk.LabelFrame(main, text="Configurations", padding=10)
        config_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=8)
        config_frame.columnconfigure(1, weight=1)

        ttk.Label(config_frame, text="Name").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(config_frame, textvariable=self.config_name_var).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(config_frame, text="Save / Update", command=self.save_current_config).grid(
            row=0,
            column=3,
            sticky="e",
            padx=(8, 0),
            pady=4,
        )
        ttk.Button(config_frame, text="New", command=self.start_new_config).grid(
            row=0,
            column=2,
            sticky="e",
            padx=(8, 0),
            pady=4,
        )
        ttk.Button(config_frame, text="Delete", command=self.delete_current_config).grid(
            row=0,
            column=4,
            sticky="e",
            padx=(8, 0),
            pady=4,
        )

        list_frame = ttk.Frame(main)
        list_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=8)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.config_list = tk.Listbox(list_frame, height=8, exportselection=False)
        self.config_list.grid(row=0, column=0, sticky="nsew")
        self.config_list.bind("<<ListboxSelect>>", self.load_selected_config)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.config_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.config_list.configure(yscrollcommand=scrollbar.set)

        action_frame = ttk.Frame(main)
        action_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        action_frame.columnconfigure(2, weight=1)

        ttk.Button(action_frame, text="?", width=3, command=self.show_help).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
        )
        ttk.Button(action_frame, text="Edit Badge Cost", command=self.show_badge_cost_editor).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(0, 8),
        )
        ttk.Label(action_frame, textvariable=self.status_var).grid(row=0, column=2, sticky="w")
        self.set_button = ttk.Button(action_frame, text="Set", command=self.start_set_run)
        self.set_button.grid(row=0, column=3, sticky="e")

    def _refresh_config_list(self):
        selected_name = self.config_name_var.get()
        self.config_list.delete(0, tk.END)
        for name in sorted(self.configs):
            self.config_list.insert(tk.END, name)
            if name == selected_name:
                self.config_list.selection_set(tk.END)

    def _current_badge_counts(self):
        return {badge: var.get() for badge, var in self.badge_vars.items()}

    def _prerequisite_errors(self):
        return configuration_prerequisite_errors(self._current_badge_counts())

    def _next_cost_label(self, badge, locked):
        if locked:
            return "Locked"
        next_cost = next_level_kakera_cost(self._current_badge_counts(), badge, self.badge_data)
        if next_cost["state"] == "max":
            return "Max"
        if next_cost["state"] == "locked":
            return "Locked"
        return f"Next {format_kakera(next_cost['cost'])}"

    def _update_set_button_state(self, errors=None):
        if not hasattr(self, "set_button"):
            return
        if errors is None:
            errors = self._prerequisite_errors()
        state = tk.DISABLED if self.is_sending or errors else tk.NORMAL
        self.set_button.configure(state=state)

    def _update_badge_ui_state(self, *_args):
        if not self.badge_vars or self.is_updating_badge_ui:
            return
        self.is_updating_badge_ui = True
        try:
            raw_counts = self._current_badge_counts()
            cleared_counts = clear_locked_badges(raw_counts)
            normalized_counts = normalize_badge_counts(raw_counts)
            cleared_badges = [
                badge for badge in BADGES if cleared_counts[badge] != normalized_counts[badge]
            ]
            for badge in cleared_badges:
                self.badge_vars[badge].set(str(cleared_counts[badge]))

            counts = self._current_badge_counts()
            for badge in BADGES:
                status = badge_prerequisite_status(badge, counts)
                locked = not status["unlocked"]
                if badge in self.badge_spinboxes:
                    self.badge_spinboxes[badge].configure(state=tk.DISABLED if locked else tk.NORMAL)
                if badge in self.badge_next_cost_vars:
                    self.badge_next_cost_vars[badge].set(self._next_cost_label(badge, locked))
            errors = configuration_prerequisite_errors(counts)
            if errors:
                self.total_cost_var.set("Total cost: prerequisites needed")
                self.status_var.set("Locked badge prerequisites missing")
            else:
                self.total_cost_var.set(
                    f"Total cost: {format_kakera(total_kakera_cost(counts, self.badge_data))} kakera"
                )
                if cleared_badges:
                    self.status_var.set("Locked badge reset to 0")
                elif self.status_var.get() == "Locked badge prerequisites missing":
                    self.status_var.set("Ready")
            self._update_set_button_state(errors)
        finally:
            self.is_updating_badge_ui = False

    def _current_config(self):
        return {"badges": normalize_badge_counts(self._current_badge_counts())}

    def _apply_config(self, name, config):
        normalized = ConfigStore._normalize_entry(config)
        self.config_name_var.set(name)
        for badge in BADGES:
            self.badge_vars[badge].set(normalized["badges"][badge])
        self._update_badge_ui_state()

    def save_current_config(self):
        name = self.config_name_var.get().strip()
        if not name:
            self.show_popup(APP_TITLE, "Enter a configuration name before saving.")
            return
        errors = self._prerequisite_errors()
        if errors:
            self.show_popup(APP_TITLE, errors[0])
            return
        self.configs[name] = self._current_config()
        try:
            self.store.save(self.configs)
            self.save_settings()
        except OSError as exc:
            self.show_popup(APP_TITLE, f"Could not save configuration: {exc}")
            return
        self.status_var.set(f"Saved configuration: {name}")
        self._refresh_config_list()

    def start_new_config(self):
        self.config_name_var.set("")
        self.config_list.selection_clear(0, tk.END)
        for badge, count in empty_badge_counts().items():
            self.badge_vars[badge].set(str(count))
        self.status_var.set("New configuration")
        self._update_badge_ui_state()

    def _selected_config_name(self):
        selection = self.config_list.curselection()
        if selection:
            return self.config_list.get(selection[0])
        return self.config_name_var.get().strip()

    def delete_current_config(self):
        name = self._selected_config_name()
        if not name:
            self.show_popup(APP_TITLE, "Select or enter a configuration to delete.")
            return
        if name not in self.configs:
            self.show_popup(APP_TITLE, f"No saved configuration named {name}.")
            return
        del self.configs[name]
        try:
            self.store.save(self.configs)
        except OSError as exc:
            self.show_popup(APP_TITLE, f"Could not delete configuration: {exc}")
            return
        if self.config_name_var.get().strip() == name:
            self.config_name_var.set("")
        self.status_var.set(f"Deleted configuration: {name}")
        self._refresh_config_list()

    def load_selected_config(self, _event=None):
        selection = self.config_list.curselection()
        if not selection:
            return
        name = self.config_list.get(selection[0])
        self._apply_config(name, self.configs[name])
        self.status_var.set(f"Loaded configuration: {name}")

    def show_help(self):
        popup = SilentPopup(self.root, f"{APP_TITLE} Help", wrap_source=self.root)
        for line in HELP_LINES:
            if line == "2. Enter your discord userID.":
                popup.add_help_line_with_user_id_link(lambda: self.show_user_id_help(popup.window))
            else:
                popup.add_line(line)
        popup.show()

    def show_user_id_help(self, parent=None):
        self.show_popup(f"{APP_TITLE} - Discord userID", USER_ID_HELP_TEXT, parent=parent)

    def show_badge_cost_editor(self):
        BadgeCostEditor(self.root, self.badge_data, self.save_badge_costs).show()

    def save_badge_costs(self, badge_data):
        self.badge_data_store.save(badge_data)
        self.badge_data = normalize_badge_data(badge_data)
        self._update_badge_ui_state()
        self.status_var.set("Saved badge costs")

    def show_badge_info(self, badge):
        self.show_popup(
            f"{APP_TITLE} - {badge.title()} Badge",
            "\n".join(badge_info_lines(badge, self.badge_data)),
        )

    def show_popup(self, title, message, parent=None):
        SilentPopup(parent or self.root, title, message.splitlines(), wrap_source=self.root).show()

    def _current_settings(self):
        return {
            "user_id": self.user_id_var.get(),
            "delay": self.delay_var.get(),
        }

    def _load_settings(self):
        settings = self.settings_store.load()
        self.user_id_var.set(settings["user_id"])
        self.delay_var.set(str(settings["delay"]))
        self.settings_store.save(settings)

    def save_settings(self):
        self.settings_store.save(self._current_settings())

    def close(self):
        try:
            self.save_settings()
        except OSError:
            pass
        self.root.destroy()

    def start_set_run(self):
        try:
            user_id = validate_user_id(self.user_id_var.get())
            delay = validate_delay(self.delay_var.get())
            errors = self._prerequisite_errors()
            if errors:
                raise ValueError(errors[0])
            commands = build_command_sequence(user_id, self._current_badge_counts())
        except ValueError as exc:
            self.show_popup(APP_TITLE, str(exc))
            return

        self.is_sending = True
        self._update_set_button_state([])
        self.status_var.set(f"Sending {len(commands)} messages...")
        worker = threading.Thread(
            target=self._send_worker,
            args=(commands, delay),
            daemon=True,
        )
        worker.start()

    def _send_worker(self, commands, delay):
        try:
            DiscordSender(delay).send_messages(commands)
        except Exception as exc:
            self.root.after(0, lambda: self._finish_set_run(error=str(exc)))
            return
        self.root.after(0, self._finish_set_run)

    def _focus_app_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        try:
            ctypes.WinDLL("user32", use_last_error=True).SetForegroundWindow(self.root.winfo_id())
        except Exception:
            pass

    def _finish_set_run(self, error=None):
        self._focus_app_window()
        self.is_sending = False
        self._update_badge_ui_state()
        if error:
            self.status_var.set("Send failed")
            self.show_popup(APP_TITLE, error)
            return
        try:
            self.save_settings()
        except OSError:
            pass
        result_name = find_matching_config_name(
            self.config_name_var.get(),
            self.configs,
            self._current_badge_counts(),
        )
        result_message = format_set_result_message(result_name, self._current_badge_counts())
        self.status_var.set(result_message)
        self.show_popup(APP_TITLE, result_message)


def main():
    enable_dpi_awareness()
    root = tk.Tk()
    configure_tk_scaling(root)
    KakeraSetterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
