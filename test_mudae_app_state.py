import tempfile
import unittest
from pathlib import Path

from mudae_badge_setter import (
    BADGE_DATA_FILENAME,
    BadgeDataStore,
    CONFIG_FILENAME,
    ConfigStore,
    HELP_LINES,
    POPUP_HORIZONTAL_PADDING,
    HELP_POPUP_WIDTH_FRACTION,
    SETTINGS_FILENAME,
    SettingsStore,
    USER_ID_HELP_TEXT,
    app_base_dir,
    app_data_dir,
    cleanup_obsolete_runtime_files,
    empty_badge_counts,
    migrate_runtime_file,
    popup_source_width,
    popup_window_width,
    popup_wraplength,
    runtime_file_path,
    screen_fraction_geometry,
)


class AppPersistenceTests(unittest.TestCase):
    def test_settings_store_saves_only_user_id_delay_and_budget(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "settings.json"
            store = SettingsStore(path)
            store.save(
                {
                    "config_name": "main",
                    "user_id": "718568383347556424",
                    "delay": "1.5",
                    "budget": "100,000",
                    "badges": {"bronze": 2, "diamond": 4},
                }
            )

            raw_file = path.read_text(encoding="utf-8")
            loaded = SettingsStore(path).load()

        self.assertNotIn("config_name", raw_file)
        self.assertNotIn("badges", raw_file)
        self.assertEqual(loaded["user_id"], "718568383347556424")
        self.assertEqual(loaded["delay"], 1.5)
        self.assertEqual(loaded["budget"], 100000)

    def test_config_store_saves_only_badge_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "configs.json"
            store = ConfigStore(path)
            store.save(
                {
                    "main": {
                        "user_id": "718568383347556424",
                        "delay": "1.5",
                        "badges": {"bronze": 2, "diamond": 4},
                    }
                }
            )

            raw_file = path.read_text(encoding="utf-8")
            loaded = ConfigStore(path).load()

        self.assertNotIn("user_id", raw_file)
        self.assertNotIn("delay", raw_file)
        self.assertEqual(loaded["main"]["badges"]["bronze"], 2)
        self.assertEqual(loaded["main"]["badges"]["diamond"], 4)

    def test_empty_badge_counts_returns_all_zeroes(self):
        self.assertEqual(
            empty_badge_counts(),
            {
                "bronze": 0,
                "silver": 0,
                "gold": 0,
                "sapphire": 0,
                "ruby": 0,
                "emerald": 0,
                "diamond": 0,
            },
        )

    def test_badge_data_store_creates_default_runtime_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / BADGE_DATA_FILENAME
            store = BadgeDataStore(path)

            loaded = store.load()

            self.assertTrue(path.exists())
            self.assertEqual(loaded["badges"]["bronze"]["costs"]["1"], 1000)
            self.assertEqual(loaded["badges"]["ruby"]["costs"]["4"], 28000)

    def test_badge_data_store_saves_edited_costs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / BADGE_DATA_FILENAME
            store = BadgeDataStore(path)
            data = store.load()
            data["badges"]["ruby"]["costs"]["4"] = 12345

            store.save(data)
            loaded = BadgeDataStore(path).load()

        self.assertEqual(loaded["badges"]["ruby"]["costs"]["4"], 12345)

    def test_help_text_explains_core_workflow(self):
        help_text = "\n".join(HELP_LINES)
        self.assertIn("Open Discord", help_text)
        self.assertIn("Enter your discord userID.", help_text)
        self.assertIn("Message delay", help_text)
        self.assertIn("Budget kakera", help_text)
        self.assertIn("Edit Badge Cost", help_text)
        self.assertIn("Set", help_text)

    def test_user_id_help_text_explains_copy_id_steps(self):
        self.assertIn("gear icon", USER_ID_HELP_TEXT)
        self.assertIn("Advanced", USER_ID_HELP_TEXT)
        self.assertIn("Developer Mode", USER_ID_HELP_TEXT)
        self.assertIn("Copy ID", USER_ID_HELP_TEXT)

    def test_screen_fraction_geometry_uses_35_percent_width_and_40_percent_height(self):
        self.assertEqual(screen_fraction_geometry(2560, 1440), "896x576")

    def test_popup_window_width_uses_30_percent_of_screen_width(self):
        self.assertEqual(popup_window_width(2560), int(2560 * HELP_POPUP_WIDTH_FRACTION))

    def test_popup_wraplength_fits_inside_popup_padding(self):
        self.assertEqual(popup_wraplength(2560), popup_window_width(2560) - POPUP_HORIZONTAL_PADDING)

    def test_popup_source_width_uses_screen_width_not_app_width(self):
        class FakeWindow:
            def __init__(self):
                self.updated = False

            def update_idletasks(self):
                self.updated = True

            def winfo_width(self):
                return 900

            def winfo_screenwidth(self):
                return 2560

        window = FakeWindow()

        self.assertEqual(popup_source_width(window), 2560)
        self.assertTrue(window.updated)

    def test_app_base_dir_uses_exe_folder_when_frozen(self):
        base_dir = app_base_dir(
            is_frozen=True,
            executable=r"C:\Tools\Mudae Badge Setter.exe",
            source_file=r"C:\Temp\_MEI12345\mudae_badge_setter.py",
        )

        self.assertEqual(base_dir, Path(r"C:\Tools"))

    def test_runtime_file_path_uses_appdata_folder(self):
        path = runtime_file_path(
            CONFIG_FILENAME,
            appdata=r"C:\Users\Test\AppData\Roaming",
        )

        self.assertEqual(
            path,
            Path(r"C:\Users\Test\AppData\Roaming\Mudae Badge Setter\configs.json"),
        )

    def test_settings_filename_is_plain_settings_json(self):
        path = runtime_file_path(
            SETTINGS_FILENAME,
            appdata=r"C:\Users\Test\AppData\Roaming",
        )

        self.assertEqual(
            path,
            Path(r"C:\Users\Test\AppData\Roaming\Mudae Badge Setter\settings.json"),
        )

    def test_badge_data_filename_uses_appdata_folder(self):
        path = runtime_file_path(
            BADGE_DATA_FILENAME,
            appdata=r"C:\Users\Test\AppData\Roaming",
        )

        self.assertEqual(
            path,
            Path(r"C:\Users\Test\AppData\Roaming\Mudae Badge Setter\badge_data.json"),
        )

    def test_app_data_dir_falls_back_when_appdata_is_missing(self):
        self.assertEqual(
            app_data_dir(appdata="", home=Path(r"C:\Users\Test")),
            Path(r"C:\Users\Test\AppData\Roaming\Mudae Badge Setter"),
        )

    def test_migrate_runtime_file_copies_legacy_file_when_target_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            legacy = root / "legacy.json"
            target = root / "appdata" / "state.json"
            legacy.write_text('{"ok": true}', encoding="utf-8")

            migrated = migrate_runtime_file(target, [legacy])

            self.assertTrue(migrated)
            self.assertEqual(target.read_text(encoding="utf-8"), '{"ok": true}')

    def test_migrate_runtime_file_keeps_existing_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            legacy = root / "legacy.json"
            target = root / "appdata" / "state.json"
            legacy.write_text('{"legacy": true}', encoding="utf-8")
            target.parent.mkdir(parents=True)
            target.write_text('{"current": true}', encoding="utf-8")

            migrated = migrate_runtime_file(target, [legacy])

            self.assertFalse(migrated)
            self.assertEqual(target.read_text(encoding="utf-8"), '{"current": true}')

    def test_cleanup_obsolete_runtime_files_removes_old_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old_config = root / "mudae_kakera_configs.json"
            old_settings = root / "mudae_kakera_last_state.json"
            old_config.write_text("{}", encoding="utf-8")
            old_settings.write_text("{}", encoding="utf-8")

            removed = cleanup_obsolete_runtime_files([old_config, old_settings])

            self.assertEqual(removed, 2)
            self.assertFalse(old_config.exists())
            self.assertFalse(old_settings.exists())


if __name__ == "__main__":
    unittest.main()
