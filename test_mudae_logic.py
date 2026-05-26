import unittest

from mudae_logic import (
    BADGES,
    DEFAULT_DELAY,
    build_command_sequence,
    normalize_config,
    validate_delay,
    validate_user_id,
)


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


if __name__ == "__main__":
    unittest.main()
