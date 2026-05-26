import tempfile
import unittest
from pathlib import Path

from mudae_kakera_setter import AppStateStore, HELP_TEXT


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
        self.assertIn("Open Discord", HELP_TEXT)
        self.assertIn("numeric Discord user ID", HELP_TEXT)
        self.assertIn("Message delay", HELP_TEXT)
        self.assertIn("Set", HELP_TEXT)


if __name__ == "__main__":
    unittest.main()
