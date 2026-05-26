import unittest

from mudae_logic import (
    BADGES,
    DEFAULT_DELAY,
    badge_info_lines,
    badge_prerequisite_status,
    build_command_sequence,
    clear_locked_badges,
    configuration_prerequisite_errors,
    default_configurations,
    find_matching_config_name,
    format_set_result_message,
    next_level_kakera_cost,
    seed_default_configurations,
    normalize_config,
    total_kakera_cost,
    validate_delay,
    validate_user_id,
)


class MudaeLogicTests(unittest.TestCase):
    def test_build_command_sequence_formats_refund_and_sends_badge_counts(self):
        counts = {badge: 0 for badge in BADGES}
        counts["bronze"] = 2
        counts["silver"] = 1

        commands = build_command_sequence("718568383347556424", counts)

        self.assertEqual(
            commands,
            [
                "$kakerarefund <@718568383347556424>",
                "confirm",
                "$bronze 2",
                "y",
                "$silver 1",
                "y",
            ],
        )

    def test_build_command_sequence_sends_ruby_four_after_prerequisites(self):
        counts = {badge: 0 for badge in BADGES}
        counts["bronze"] = 4
        counts["silver"] = 2
        counts["gold"] = 2
        counts["ruby"] = 4

        commands = build_command_sequence("718568383347556424", counts)

        self.assertEqual(
            commands,
            [
                "$kakerarefund <@718568383347556424>",
                "confirm",
                "$bronze 2",
                "y",
                "$silver 2",
                "y",
                "$gold 2",
                "y",
                "$ruby 4",
                "y",
                "$bronze 2",
                "y",
            ],
        )

    def test_default_configurations_include_minimum_cost_targets(self):
        defaults = default_configurations()

        self.assertEqual(
            defaults["Ruby 4 Minimum Cost"]["badges"],
            {
                "bronze": 2,
                "silver": 2,
                "gold": 2,
                "sapphire": 0,
                "ruby": 4,
                "emerald": 0,
                "diamond": 0,
            },
        )
        self.assertEqual(
            defaults["Sapphire 4 Minimum Cost"]["badges"],
            {
                "bronze": 2,
                "silver": 2,
                "gold": 2,
                "sapphire": 4,
                "ruby": 0,
                "emerald": 0,
                "diamond": 0,
            },
        )
        self.assertEqual(
            defaults["Emerald 4 Minimum Cost"]["badges"],
            {
                "bronze": 4,
                "silver": 4,
                "gold": 0,
                "sapphire": 0,
                "ruby": 0,
                "emerald": 4,
                "diamond": 0,
            },
        )

    def test_seed_default_configurations_only_when_empty(self):
        custom = {"custom": {"badges": {"bronze": 1}}}

        self.assertEqual(seed_default_configurations(custom), custom)
        self.assertEqual(set(seed_default_configurations({})), set(default_configurations()))

    def test_total_kakera_cost_splits_prerequisite_and_discounted_levels(self):
        counts = {badge: 0 for badge in BADGES}
        counts.update({"bronze": 4, "silver": 2, "gold": 2, "ruby": 4})

        self.assertEqual(total_kakera_cost(counts), 93250)

    def test_next_level_kakera_cost_uses_ruby_discount_when_active_in_plan(self):
        counts = {badge: 0 for badge in BADGES}
        counts.update({"bronze": 2, "silver": 2, "gold": 2, "ruby": 4})

        next_cost = next_level_kakera_cost(counts, "bronze")

        self.assertEqual(next_cost["level"], 3)
        self.assertEqual(next_cost["base_cost"], 3000)
        self.assertEqual(next_cost["cost"], 2250)
        self.assertTrue(next_cost["discounted"])

    def test_badge_prerequisite_status_reports_locked_badges(self):
        counts = {badge: 0 for badge in BADGES}

        self.assertFalse(badge_prerequisite_status("ruby", counts)["unlocked"])
        self.assertFalse(badge_prerequisite_status("emerald", counts)["unlocked"])

        counts.update({"bronze": 2, "silver": 2, "gold": 2})
        self.assertTrue(badge_prerequisite_status("ruby", counts)["unlocked"])
        self.assertTrue(badge_prerequisite_status("sapphire", counts)["unlocked"])

        counts.update({"bronze": 4, "silver": 4, "gold": 0})
        self.assertTrue(badge_prerequisite_status("emerald", counts)["unlocked"])
        self.assertTrue(badge_prerequisite_status("diamond", counts)["unlocked"])

    def test_configuration_prerequisite_errors_rejects_locked_badges(self):
        counts = {badge: 0 for badge in BADGES}
        counts["ruby"] = 4

        errors = configuration_prerequisite_errors(counts)

        self.assertEqual(len(errors), 1)
        self.assertIn("Ruby", errors[0])

    def test_clear_locked_badges_resets_ruby_when_basic_prerequisite_drops(self):
        counts = {badge: 0 for badge in BADGES}
        counts.update({"bronze": 1, "silver": 2, "gold": 2, "ruby": 4})

        cleared = clear_locked_badges(counts)

        self.assertEqual(cleared["ruby"], 0)
        self.assertEqual(cleared["bronze"], 1)

    def test_clear_locked_badges_resets_level_four_badge_when_prerequisite_drops(self):
        counts = {badge: 0 for badge in BADGES}
        counts.update({"bronze": 4, "silver": 3, "emerald": 4})

        cleared = clear_locked_badges(counts)

        self.assertEqual(cleared["emerald"], 0)
        self.assertEqual(cleared["bronze"], 4)
        self.assertEqual(cleared["silver"], 3)

    def test_badge_info_lines_include_costs_and_prerequisites(self):
        lines = badge_info_lines("ruby")
        text = "\n".join(lines)

        self.assertIn("Ruby", lines[0])
        self.assertIn("Level IV: 28,000", text)
        self.assertIn("Bronze II", text)
        self.assertIn("25% discount", text)

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
