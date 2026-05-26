import tempfile
import unittest
from pathlib import Path

from mudae_kakera_setter import (
    AppStateStore,
    HELP_LINES,
    USER_ID_HELP_TEXT,
    app_base_dir,
    app_data_dir,
    migrate_runtime_file,
    runtime_file_path,
    screen_fraction_geometry,
)


class AppStateStoreTests(unittest.TestCase):
    def test_save_and_load_persists_last_ui_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "last_state.json"
            store = AppStateStore(path)
            store.save(
                {
                    "config_name": "main",
                    "user_id": "718568383347556424",
                    "delay": "1.5",
                    "badges": {"bronze": 2, "diamond": 4},
                }
            )

            loaded = AppStateStore(path).load()

        self.assertEqual(loaded["config_name"], "main")
        self.assertEqual(loaded["user_id"], "718568383347556424")
        self.assertEqual(loaded["delay"], 1.5)
        self.assertEqual(loaded["badges"]["bronze"], 2)
        self.assertEqual(loaded["badges"]["diamond"], 4)

    def test_help_text_explains_core_workflow(self):
        help_text = "\n".join(HELP_LINES)
        self.assertIn("Open Discord", help_text)
        self.assertIn("Enter your discord userID.", help_text)
        self.assertIn("Message delay", help_text)
        self.assertIn("Set", help_text)

    def test_user_id_help_text_explains_copy_id_steps(self):
        self.assertIn("gear icon", USER_ID_HELP_TEXT)
        self.assertIn("Advanced", USER_ID_HELP_TEXT)
        self.assertIn("Developer Mode", USER_ID_HELP_TEXT)
        self.assertIn("Copy ID", USER_ID_HELP_TEXT)

    def test_screen_fraction_geometry_uses_30_percent_of_screen(self):
        self.assertEqual(screen_fraction_geometry(2560, 1440), "768x432")

    def test_app_base_dir_uses_exe_folder_when_frozen(self):
        base_dir = app_base_dir(
            is_frozen=True,
            executable=r"C:\Tools\Mudae Badge Setter.exe",
            source_file=r"C:\Temp\_MEI12345\mudae_kakera_setter.py",
        )

        self.assertEqual(base_dir, Path(r"C:\Tools"))

    def test_runtime_file_path_uses_appdata_folder(self):
        path = runtime_file_path(
            "mudae_kakera_configs.json",
            appdata=r"C:\Users\Test\AppData\Roaming",
        )

        self.assertEqual(
            path,
            Path(r"C:\Users\Test\AppData\Roaming\Mudae Badge Setter\mudae_kakera_configs.json"),
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


if __name__ == "__main__":
    unittest.main()
