# Mudae Kakera Setter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows Python UI app that saves Mudae badge presets and sends the configured command sequence through the open Discord desktop client.

**Architecture:** Keep pure command/config behavior in a testable module, keep Windows desktop automation in a small adapter, and keep the `tkinter` UI as the orchestration layer. The UI calls pure validation/build helpers before invoking the Discord sender.

**Tech Stack:** Python standard library only: `tkinter`, `json`, `pathlib`, `threading`, `ctypes`, and `unittest`.

---

## File Structure

- `mudae_logic.py`: Badge constants, validation helpers, command-sequence builder, and config normalization.
- `test_mudae_logic.py`: Unit tests for pure behavior using `unittest`.
- `mudae_kakera_setter.py`: `tkinter` app, config file persistence, Windows Discord automation, and CLI entry point.
- `README.md`: Usage notes, safety notes, and manual verification instructions.
- `mudae_kakera_configs.json`: Runtime-generated user config file, not committed.
- `.gitignore`: Excludes runtime config and Python cache files.

## Task 1: Command Sequence Logic

**Files:**
- Create: `test_mudae_logic.py`
- Create: `mudae_logic.py`

- [ ] **Step 1: Write failing tests**

```python
import unittest

from mudae_logic import BADGES, build_command_sequence, validate_delay, validate_user_id


class MudaeLogicTests(unittest.TestCase):
    def test_build_command_sequence_formats_refund_and_repeats_badges(self):
        counts = {badge: 0 for badge in BADGES}
        counts["bronze"] = 2
        counts["diamond"] = 1

        commands = build_command_sequence("718568383347556424", counts)

        self.assertEqual(
            commands,
            [
                "$kakerarefund <@718568383347556424>",
                "confirm",
                "$bronze",
                "y",
                "$bronze",
                "y",
                "$diamond",
                "y",
            ],
        )

    def test_validate_user_id_accepts_digits_only(self):
        self.assertEqual(validate_user_id(" 718568383347556424 "), "718568383347556424")

    def test_validate_user_id_rejects_mention_format(self):
        with self.assertRaises(ValueError):
            validate_user_id("<@718568383347556424>")

    def test_validate_delay_accepts_positive_float(self):
        self.assertEqual(validate_delay("0.8"), 0.8)

    def test_validate_delay_rejects_zero(self):
        with self.assertRaises(ValueError):
            validate_delay("0")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest test_mudae_logic.py -v`

Expected: fail because `mudae_logic` does not exist yet.

- [ ] **Step 3: Implement minimal command logic**

```python
BADGES = ("bronze", "silver", "gold", "sapphire", "ruby", "emerald", "diamond")


def validate_user_id(raw_user_id):
    user_id = raw_user_id.strip()
    if not user_id or not user_id.isdigit():
        raise ValueError("Enter a numeric Discord user ID, not a mention.")
    return user_id


def validate_delay(raw_delay):
    try:
        delay = float(raw_delay)
    except ValueError as exc:
        raise ValueError("Delay must be a positive number.") from exc
    if delay <= 0:
        raise ValueError("Delay must be greater than 0.")
    return delay


def clamp_badge_count(value):
    count = int(value)
    return max(0, min(4, count))


def normalize_badge_counts(raw_counts):
    return {badge: clamp_badge_count(raw_counts.get(badge, 0)) for badge in BADGES}


def build_command_sequence(raw_user_id, raw_badge_counts):
    user_id = validate_user_id(raw_user_id)
    badge_counts = normalize_badge_counts(raw_badge_counts)
    commands = [f"$kakerarefund <@{user_id}>", "confirm"]
    for badge in BADGES:
        for _ in range(badge_counts[badge]):
            commands.extend([f"${badge}", "y"])
    return commands
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest test_mudae_logic.py -v`

Expected: 5 tests pass.

## Task 2: Config Normalization

**Files:**
- Modify: `test_mudae_logic.py`
- Modify: `mudae_logic.py`

- [ ] **Step 1: Add failing config tests**

```python
from mudae_logic import DEFAULT_DELAY, normalize_config


class MudaeLogicTests(unittest.TestCase):
    def test_normalize_config_fills_defaults_and_clamps_counts(self):
        config = normalize_config(
            {
                "user_id": "718568383347556424",
                "delay": "1.2",
                "badges": {"bronze": 9, "ruby": "2"},
            }
        )

        self.assertEqual(
            config,
            {
                "user_id": "718568383347556424",
                "delay": 1.2,
                "badges": {
                    "bronze": 4,
                    "silver": 0,
                    "gold": 0,
                    "sapphire": 0,
                    "ruby": 2,
                    "emerald": 0,
                    "diamond": 0,
                },
            },
        )

    def test_normalize_config_uses_default_delay_when_invalid(self):
        config = normalize_config({"delay": "bad", "badges": {}})
        self.assertEqual(config["delay"], DEFAULT_DELAY)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest test_mudae_logic.py -v`

Expected: fail because `normalize_config` and `DEFAULT_DELAY` do not exist yet.

- [ ] **Step 3: Implement config normalization**

```python
DEFAULT_DELAY = 0.8


def normalize_config(raw_config):
    raw_config = raw_config if isinstance(raw_config, dict) else {}
    raw_badges = raw_config.get("badges", {})
    try:
        delay = validate_delay(str(raw_config.get("delay", DEFAULT_DELAY)))
    except ValueError:
        delay = DEFAULT_DELAY
    return {
        "user_id": str(raw_config.get("user_id", "")).strip(),
        "delay": delay,
        "badges": normalize_badge_counts(raw_badges if isinstance(raw_badges, dict) else {}),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest test_mudae_logic.py -v`

Expected: all tests pass.

## Task 3: Desktop App and Windows Automation

**Files:**
- Create: `mudae_kakera_setter.py`
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Create UI and sender implementation**

Implement:

- `DiscordSender` with `find_discord_window`, `focus_discord`, `click_message_box`, `send_message`, and `send_messages`.
- `KakeraSetterApp` with user ID, delay, badge spinboxes, config name, save/update button, saved config list, and `Set` button.
- JSON config load/save from `mudae_kakera_configs.json`.
- A worker thread for sending so the UI does not freeze.
- Clipboard save/restore around the send run.

- [ ] **Step 2: Run syntax and unit verification**

Run:

```bash
python -m py_compile mudae_kakera_setter.py mudae_logic.py
python -m unittest test_mudae_logic.py -v
```

Expected: compile succeeds and all tests pass.

- [ ] **Step 3: Update docs**

`README.md` must explain:

- Run with `python mudae_kakera_setter.py`.
- Open Discord to the target channel before pressing `Set`.
- The script will briefly focus Discord and then return focus to the app.
- Enter only the numeric user ID.
- Increase delay if Discord or the internet connection misses messages.

## Task 4: Final Verification

**Files:**
- Read all created files.

- [ ] **Step 1: Run fresh verification**

Run:

```bash
python -m unittest test_mudae_logic.py -v
python -m py_compile mudae_kakera_setter.py mudae_logic.py
```

Expected: tests pass and compilation exits with status 0.

- [ ] **Step 2: Check git status**

Run: `git status --short`

Expected: only intentional files are modified or untracked.

- [ ] **Step 3: Commit implementation**

Run:

```bash
git add .gitignore README.md mudae_logic.py test_mudae_logic.py mudae_kakera_setter.py docs/superpowers/plans/2026-05-26-mudae-kakera-setter.md
git commit -m "feat: add mudae kakera setter app"
```
