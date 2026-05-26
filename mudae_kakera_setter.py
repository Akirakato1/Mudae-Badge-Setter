import ctypes
import json
import threading
import time
import tkinter as tk
from ctypes import wintypes
from pathlib import Path
from tkinter import ttk

from mudae_logic import (
    BADGES,
    DEFAULT_DELAY,
    build_command_sequence,
    find_matching_config_name,
    format_set_result_message,
    normalize_config,
    validate_delay,
    validate_user_id,
)


CONFIG_PATH = Path(__file__).with_name("mudae_kakera_configs.json")
STATE_PATH = Path(__file__).with_name("mudae_kakera_last_state.json")
APP_TITLE = "Mudae Kakera Setter"
POINTS_PER_INCH = 72.0
WINDOW_SCREEN_FRACTION = 0.30
HELP_LINES = (
    "How to use this app:",
    "",
    "1. Open Discord desktop to the text channel where Mudae should receive commands.",
    "2. Enter your discord userID.",
    "3. Set the Message delay. Use a larger value if Discord misses messages.",
    "4. Set badge counts from 0 to 4.",
    "5. Enter a configuration name and click Save / Update to save the current settings.",
    "6. Click a saved configuration to load it into the fields.",
    "7. Click Set to run the sequence.",
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


def screen_fraction_geometry(screen_width, screen_height, fraction=WINDOW_SCREEN_FRACTION):
    width = max(1, int(screen_width * fraction))
    height = max(1, int(screen_height * fraction))
    return f"{width}x{height}"


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
        return {str(name): normalize_config(config) for name, config in data.items()}

    def save(self, configs):
        normalized = {str(name): normalize_config(config) for name, config in configs.items()}
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(normalized, file, indent=2, sort_keys=True)


class SilentPopup:
    def __init__(self, parent, title, lines=None):
        self.parent = parent
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
        ttk.Label(self.frame, text=text, wraplength=460, justify="left").grid(
            row=self._row,
            column=0,
            sticky="w",
            pady=(0, 4),
        )
        self._row += 1

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
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = parent_x + max(0, int((parent_width - width) / 2))
        y = parent_y + max(0, int((parent_height - height) / 2))
        self.window.geometry(f"+{x}+{y}")

    def close(self):
        self.window.grab_release()
        self.window.destroy()


class AppStateStore:
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
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(normalized, file, indent=2, sort_keys=True)

    @staticmethod
    def _normalize(state):
        state = state if isinstance(state, dict) else {}
        config = normalize_config(state)
        config["config_name"] = str(state.get("config_name", "")).strip()
        return config


class KakeraSetterApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(
            screen_fraction_geometry(self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        )
        self.root.minsize(360, 300)

        self.store = ConfigStore(CONFIG_PATH)
        self.state_store = AppStateStore(STATE_PATH)
        self.configs = self.store.load()
        self.badge_vars = {}

        self.user_id_var = tk.StringVar()
        self.delay_var = tk.StringVar(value=str(DEFAULT_DELAY))
        self.config_name_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()
        self._load_last_state()
        self._refresh_config_list()
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
            ttk.Label(badge_frame, text=badge.title()).grid(row=0, column=index, padx=4, pady=(0, 4))
            var = tk.StringVar(value="0")
            self.badge_vars[badge] = var
            tk.Spinbox(
                badge_frame,
                from_=0,
                to=4,
                width=4,
                textvariable=var,
                justify="center",
                wrap=False,
            ).grid(row=1, column=index, padx=4)

        config_frame = ttk.LabelFrame(main, text="Configurations", padding=10)
        config_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=8)
        config_frame.columnconfigure(1, weight=1)

        ttk.Label(config_frame, text="Name").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(config_frame, textvariable=self.config_name_var).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(config_frame, text="Save / Update", command=self.save_current_config).grid(
            row=0,
            column=2,
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
        action_frame.columnconfigure(1, weight=1)

        ttk.Button(action_frame, text="?", width=3, command=self.show_help).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
        )
        ttk.Label(action_frame, textvariable=self.status_var).grid(row=0, column=1, sticky="w")
        self.set_button = ttk.Button(action_frame, text="Set", command=self.start_set_run)
        self.set_button.grid(row=0, column=2, sticky="e")

    def _refresh_config_list(self):
        selected_name = self.config_name_var.get()
        self.config_list.delete(0, tk.END)
        for name in sorted(self.configs):
            self.config_list.insert(tk.END, name)
            if name == selected_name:
                self.config_list.selection_set(tk.END)

    def _current_badge_counts(self):
        return {badge: var.get() for badge, var in self.badge_vars.items()}

    def _current_config(self):
        return normalize_config(
            {
                "user_id": self.user_id_var.get(),
                "delay": self.delay_var.get(),
                "badges": self._current_badge_counts(),
            }
        )

    def _apply_config(self, name, config):
        normalized = normalize_config(config)
        self.config_name_var.set(name)
        self.user_id_var.set(normalized["user_id"])
        self.delay_var.set(str(normalized["delay"]))
        for badge in BADGES:
            self.badge_vars[badge].set(normalized["badges"][badge])

    def save_current_config(self):
        name = self.config_name_var.get().strip()
        if not name:
            self.show_popup(APP_TITLE, "Enter a configuration name before saving.")
            return
        self.configs[name] = self._current_config()
        try:
            self.store.save(self.configs)
            self.save_last_state()
        except OSError as exc:
            self.show_popup(APP_TITLE, f"Could not save configuration: {exc}")
            return
        self.status_var.set(f"Saved configuration: {name}")
        self._refresh_config_list()

    def load_selected_config(self, _event=None):
        selection = self.config_list.curselection()
        if not selection:
            return
        name = self.config_list.get(selection[0])
        self._apply_config(name, self.configs[name])
        self.status_var.set(f"Loaded configuration: {name}")

    def show_help(self):
        popup = SilentPopup(self.root, f"{APP_TITLE} Help")
        for line in HELP_LINES:
            if line == "2. Enter your discord userID.":
                popup.add_help_line_with_user_id_link(lambda: self.show_user_id_help(popup.window))
            else:
                popup.add_line(line)
        popup.show()

    def show_user_id_help(self, parent=None):
        self.show_popup(f"{APP_TITLE} - Discord userID", USER_ID_HELP_TEXT, parent=parent)

    def show_popup(self, title, message, parent=None):
        SilentPopup(parent or self.root, title, message.splitlines()).show()

    def _last_state(self):
        state = self._current_config()
        state["config_name"] = self.config_name_var.get().strip()
        return state

    def _load_last_state(self):
        state = self.state_store.load()
        self._apply_config(state["config_name"], state)

    def save_last_state(self):
        self.state_store.save(self._last_state())

    def close(self):
        try:
            self.save_last_state()
        except OSError:
            pass
        self.root.destroy()

    def start_set_run(self):
        try:
            user_id = validate_user_id(self.user_id_var.get())
            delay = validate_delay(self.delay_var.get())
            commands = build_command_sequence(user_id, self._current_badge_counts())
        except ValueError as exc:
            self.show_popup(APP_TITLE, str(exc))
            return

        self.set_button.configure(state=tk.DISABLED)
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
        self.set_button.configure(state=tk.NORMAL)
        if error:
            self.status_var.set("Send failed")
            self.show_popup(APP_TITLE, error)
            return
        try:
            self.save_last_state()
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
