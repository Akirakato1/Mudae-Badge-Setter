import unittest

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


class MudaeLogicTests(unittest.TestCase):
    def test_build_command_sequence_formats_refund_and_sends_badge_counts(self):
        counts = {badge: 0 for badge in BADGES}
        counts["bronze"] = 2
        counts["diamond"] = 1

        commands = build_command_sequence("718568383347556424", counts)

        self.assertEqual(
            commands,
            [
                "$kakerarefund <@718568383347556424>",
                "confirm",
                "$bronze 2",
                "y",
                "$diamond 1",
                "y",
            ],
        )

    def test_build_command_sequence_sends_ruby_four_first(self):
        counts = {badge: 0 for badge in BADGES}
        counts["bronze"] = 2
        counts["ruby"] = 4
        counts["diamond"] = 1

        commands = build_command_sequence("718568383347556424", counts)

        self.assertEqual(
            commands,
            [
                "$kakerarefund <@718568383347556424>",
                "confirm",
                "$ruby 4",
                "y",
                "$bronze 2",
                "y",
                "$diamond 1",
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

    def test_normalize_config_defaults_invalid_badge_count(self):
        config = normalize_config({"badges": {"gold": "bad"}})
        self.assertEqual(config["badges"]["gold"], 0)

    def test_format_set_result_message_uses_configuration_name(self):
        counts = {badge: 0 for badge in BADGES}
        self.assertEqual(format_set_result_message("main badges", counts), "Set to main badges")

    def test_format_set_result_message_uses_badge_sequence_without_name(self):
        counts = {badge: 0 for badge in BADGES}
        counts["bronze"] = 3
        counts["silver"] = 4
        counts["gold"] = 2

        self.assertEqual(format_set_result_message("", counts), "Set to 3420000")

    def test_find_matching_config_name_prefers_current_saved_name(self):
        counts = {badge: 0 for badge in BADGES}
        counts["ruby"] = 2
        configs = {
            "other": {"badges": {"ruby": 2}},
            "main": {"badges": {"ruby": 2}},
        }

        self.assertEqual(find_matching_config_name("main", configs, counts), "main")

    def test_find_matching_config_name_returns_blank_when_current_settings_are_unsaved(self):
        counts = {badge: 0 for badge in BADGES}
        counts["bronze"] = 3
        configs = {"main": {"badges": {"bronze": 2}}}

        self.assertEqual(find_matching_config_name("main", configs, counts), "")


if __name__ == "__main__":
    unittest.main()
