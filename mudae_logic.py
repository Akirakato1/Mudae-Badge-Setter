import json
from pathlib import Path


BADGES = ("bronze", "silver", "gold", "sapphire", "ruby", "emerald", "diamond")
DEFAULT_DELAY = 0.8
BASIC_UNLOCK_BADGES = ("bronze", "silver", "gold")
BASIC_PREREQUISITE_LEVELS = {"sapphire": 1, "ruby": 2, "emerald": 3}
BADGE_DATA_FILENAME = "badge_data.json"
EMBEDDED_BADGE_DATA_JSON = r"""{
  "badges": {
    "bronze": {
      "costs": {
        "1": 1000,
        "2": 2000,
        "3": 3000,
        "4": 4000
      },
      "perks": {
        "levels_1_to_3": "Each level grants +1 supplementary wishslot.",
        "level_4": "Grants +1 wishslot, and you gain +500 Kakera whenever you claim a character on your wishlist."
      },
      "prerequisites": []
    },
    "diamond": {
      "costs": {
        "1": 12000,
        "2": 24000,
        "3": 36000,
        "4": 48000
      },
      "perks": {
        "levels_1_to_4": "Unlocks specialized perks and features related to Spheres and increasing Kakera generation efficiency."
      },
      "prerequisites": []
    },
    "emerald": {
      "costs": {
        "1": 9000,
        "2": 18000,
        "3": 27000,
        "4": 36000
      },
      "perks": {
        "levels_1_to_3": "Unlocks the $resetclaimtimer ($rt) command and decreases its cooldown at higher levels.",
        "level_4": "Allows you to gain the full Kakera value of any character you claim."
      },
      "prerequisites": [
        {
          "all_of": {
            "bronze": 3,
            "gold": 3,
            "silver": 3
          }
        },
        {
          "any_two_level_4_badges": true
        }
      ]
    },
    "gold": {
      "costs": {
        "1": 3000,
        "2": 6000,
        "3": 9000,
        "4": 12000
      },
      "perks": {
        "levels_1_to_3": "Each level reduces Kakera power used when reacting to a kakera crystal by -10%.",
        "level_4": "Decreases Kakera reaction power usage by -10%, and $dailykakera fully restores Kakera reaction power."
      },
      "prerequisites": []
    },
    "ruby": {
      "costs": {
        "1": 7000,
        "2": 14000,
        "3": 21000,
        "4": 28000
      },
      "discount": {
        "applies_to": "other_badges_after_purchase",
        "level": 4,
        "percent": 25
      },
      "perks": {
        "levels_1_to_3": "Combines and enhances Bronze, Silver, and Gold perks.",
        "level_4": "Grants a permanent 25% discount on all other badges."
      },
      "prerequisites": [
        {
          "all_of": {
            "bronze": 1,
            "gold": 1,
            "silver": 1
          }
        },
        {
          "any_two_level_4_badges": true
        }
      ]
    },
    "sapphire": {
      "costs": {
        "1": 5000,
        "2": 10000,
        "3": 15000,
        "4": 20000
      },
      "perks": {
        "levels_1_to_3": "Each level gives an additional percentage chance to instantly spawn a kakera crystal when rolling a character.",
        "level_4": "Permanently converts all blue kakera reactions into yellow kakera reactions."
      },
      "prerequisites": [
        {
          "all_of": {
            "bronze": 2,
            "gold": 2,
            "silver": 2
          }
        },
        {
          "any_two_level_4_badges": true
        }
      ]
    },
    "silver": {
      "costs": {
        "1": 2000,
        "2": 4000,
        "3": 6000,
        "4": 8000
      },
      "perks": {
        "levels_1_to_3": "Each level increases your chance to roll a character on your wishlist by +25%.",
        "level_4": "Increases wish roll chance by +25%, and you gain +200 Kakera whenever someone else claims a character on your wishlist."
      },
      "prerequisites": []
    }
  },
  "default_configurations": {
    "Emerald 4 Minimum Cost": {
      "badges": {
        "bronze": 4,
        "emerald": 4,
        "silver": 4
      },
      "estimated_cost": 120000,
      "target": "emerald"
    },
    "Ruby 4 Minimum Cost": {
      "badges": {
        "bronze": 2,
        "gold": 2,
        "ruby": 4,
        "silver": 2
      },
      "estimated_cost": 88000,
      "target": "ruby"
    },
    "Sapphire 4 Minimum Cost": {
      "badges": {
        "bronze": 1,
        "gold": 1,
        "sapphire": 4,
        "silver": 1
      },
      "estimated_cost": 56000,
      "target": "sapphire"
    }
  }
}"""


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
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = 0
    return max(0, min(4, count))


def normalize_badge_counts(raw_counts):
    return {badge: clamp_badge_count(raw_counts.get(badge, 0)) for badge in BADGES}


def default_badge_data():
    return json.loads(EMBEDDED_BADGE_DATA_JSON)


def normalize_badge_data(raw_data):
    badge_data = default_badge_data()
    raw_data = raw_data if isinstance(raw_data, dict) else {}
    raw_badges = raw_data.get("badges", {})
    raw_badges = raw_badges if isinstance(raw_badges, dict) else {}

    for badge in BADGES:
        raw_badge = raw_badges.get(badge, {})
        raw_badge = raw_badge if isinstance(raw_badge, dict) else {}
        raw_costs = raw_badge.get("costs", {})
        raw_costs = raw_costs if isinstance(raw_costs, dict) else {}
        for level in range(1, 5):
            key = str(level)
            default_cost = badge_data["badges"][badge]["costs"][key]
            try:
                cost = int(raw_costs.get(key, default_cost))
            except (TypeError, ValueError):
                cost = default_cost
            badge_data["badges"][badge]["costs"][key] = max(0, cost)

    return badge_data


def load_badge_data(path=None):
    if path is None:
        path = Path(__file__).resolve().with_name(BADGE_DATA_FILENAME)
    try:
        with Path(path).open("r", encoding="utf-8") as file:
            return normalize_badge_data(json.load(file))
    except (OSError, json.JSONDecodeError):
        return default_badge_data()


def default_configurations(badge_data=None):
    badge_data = badge_data or load_badge_data()
    defaults = badge_data.get("default_configurations", {})
    return {
        str(name): {"badges": normalize_badge_counts(config.get("badges", {}))}
        for name, config in defaults.items()
        if isinstance(config, dict)
    }


def seed_default_configurations(configs, badge_data=None):
    configs = configs if isinstance(configs, dict) else {}
    if configs:
        return configs
    return default_configurations(badge_data)


def format_kakera(value):
    return f"{int(value):,}"


def badge_level_cost(badge, level, badge_data=None):
    badge_data = badge_data or load_badge_data()
    costs = badge_data.get("badges", {}).get(badge, {}).get("costs", {})
    return int(costs.get(str(level), 0))


def ruby_discount_percent(badge_data=None):
    badge_data = badge_data or load_badge_data()
    discount = badge_data.get("badges", {}).get("ruby", {}).get("discount", {})
    if discount.get("level") == 4:
        return int(discount.get("percent", 0))
    return 0


def discounted_kakera_cost(base_cost, discount_percent):
    return int(base_cost * (100 - discount_percent) / 100)


def level_four_badge_count(raw_counts, exclude=()):
    badge_counts = normalize_badge_counts(raw_counts)
    excluded = set(exclude)
    return sum(1 for badge in BADGES if badge not in excluded and badge_counts[badge] >= 4)


def prerequisite_text(badge):
    if badge in BASIC_UNLOCK_BADGES:
        return "None"
    if badge in BASIC_PREREQUISITE_LEVELS:
        level = BASIC_PREREQUISITE_LEVELS[badge]
        numeral = {1: "I", 2: "II", 3: "III"}[level]
        return f"Bronze {numeral}, Silver {numeral}, and Gold {numeral}; or any two other Level IV badges."
    return "None"


def badge_prerequisite_status(badge, raw_counts):
    badge = str(badge).lower()
    badge_counts = normalize_badge_counts(raw_counts)
    if badge not in BADGES:
        return {"unlocked": False, "reason": "Unknown badge."}
    if badge in BASIC_UNLOCK_BADGES or badge == "diamond":
        return {"unlocked": True, "reason": "No prerequisites."}
    if badge in BASIC_PREREQUISITE_LEVELS:
        required_level = BASIC_PREREQUISITE_LEVELS[badge]
        basic_unlock = all(badge_counts[required] >= required_level for required in BASIC_UNLOCK_BADGES)
        level_four_unlock = level_four_badge_count(badge_counts, exclude=(badge,)) >= 2
        if basic_unlock or level_four_unlock:
            return {"unlocked": True, "reason": "Prerequisites met."}
        numeral = {1: "I", 2: "II", 3: "III"}[required_level]
        return {
            "unlocked": False,
            "reason": f"Requires Bronze {numeral}, Silver {numeral}, and Gold {numeral}, or any two other Level IV badges.",
        }
    return {"unlocked": True, "reason": "No prerequisites."}


def configuration_prerequisite_errors(raw_counts):
    badge_counts = normalize_badge_counts(raw_counts)
    errors = []
    for badge in BADGES:
        if badge_counts[badge] > 0:
            status = badge_prerequisite_status(badge, badge_counts)
            if not status["unlocked"]:
                errors.append(f"{badge.title()} is locked. {status['reason']}")
    return errors


def clear_locked_badges(raw_counts):
    badge_counts = normalize_badge_counts(raw_counts)
    changed = True
    while changed:
        changed = False
        for badge in BADGES:
            if badge_counts[badge] > 0 and not badge_prerequisite_status(badge, badge_counts)["unlocked"]:
                badge_counts[badge] = 0
                changed = True
    return badge_counts


def command_purchase_steps(badge_counts):
    badge_counts = normalize_badge_counts(badge_counts)
    owned = {badge: 0 for badge in BADGES}
    remaining = dict(badge_counts)
    steps = []

    def buy(badge, amount):
        amount = min(max(0, amount), remaining[badge])
        if amount:
            steps.append((badge, amount))
            owned[badge] += amount
            remaining[badge] -= amount

    def buy_to_level(badge, level):
        buy(badge, min(level, badge_counts[badge]) - owned[badge])

    def level_four_count(exclude=()):
        excluded = set(exclude)
        return sum(1 for badge in BADGES if badge not in excluded and owned[badge] >= 4)

    def buy_level_four_unlocks(exclude=()):
        excluded = set(exclude)
        for badge in BADGES:
            if badge not in excluded and badge_counts[badge] >= 4 and level_four_count(excluded) < 2:
                buy_to_level(badge, 4)

    def buy_basic_unlocks(level):
        for badge in BASIC_UNLOCK_BADGES:
            buy_to_level(badge, level)

    def has_basic_unlocks(level):
        return all(owned[badge] >= level for badge in BASIC_UNLOCK_BADGES)

    def can_buy_basic_unlocks(level):
        return all(badge_counts[badge] >= level for badge in BASIC_UNLOCK_BADGES)

    def unlock_basic_or_two_level_four(badge):
        required_level = BASIC_PREREQUISITE_LEVELS[badge]
        if has_basic_unlocks(required_level) or level_four_count((badge,)) >= 2:
            return
        if can_buy_basic_unlocks(required_level):
            buy_basic_unlocks(required_level)
        else:
            buy_level_four_unlocks((badge,))

    if badge_counts["ruby"] == 4:
        unlock_basic_or_two_level_four("ruby")
        buy_to_level("ruby", 4)

    for badge in BADGES:
        if not remaining[badge]:
            continue
        if badge in BASIC_PREREQUISITE_LEVELS:
            unlock_basic_or_two_level_four(badge)
        buy(badge, remaining[badge])

    return steps


def purchase_level_items(raw_counts, badge_data=None):
    badge_counts = normalize_badge_counts(raw_counts)
    errors = configuration_prerequisite_errors(badge_counts)
    if errors:
        raise ValueError("; ".join(errors))
    badge_data = badge_data or load_badge_data()
    discount_percent = ruby_discount_percent(badge_data)
    owned = {badge: 0 for badge in BADGES}
    ruby_discount_active = False
    items = []
    for badge, amount in command_purchase_steps(badge_counts):
        for _ in range(amount):
            level = owned[badge] + 1
            base_cost = badge_level_cost(badge, level, badge_data)
            discounted = ruby_discount_active and badge != "ruby"
            cost = discounted_kakera_cost(base_cost, discount_percent) if discounted else base_cost
            items.append(
                {
                    "badge": badge,
                    "level": level,
                    "base_cost": base_cost,
                    "cost": cost,
                    "discounted": discounted,
                }
            )
            owned[badge] = level
            if badge == "ruby" and level == 4:
                ruby_discount_active = True
    return items


def total_kakera_cost(raw_counts, badge_data=None):
    return sum(item["cost"] for item in purchase_level_items(raw_counts, badge_data))


def next_level_kakera_cost(raw_counts, badge, badge_data=None):
    badge = str(badge).lower()
    if badge not in BADGES:
        return {"state": "locked", "reason": "Unknown badge."}
    badge_counts = normalize_badge_counts(raw_counts)
    current_level = badge_counts[badge]
    if current_level >= 4:
        return {"state": "max", "level": 4}
    if not badge_prerequisite_status(badge, badge_counts)["unlocked"]:
        return {
            "state": "locked",
            "level": current_level + 1,
            "reason": badge_prerequisite_status(badge, badge_counts)["reason"],
        }
    target_counts = dict(badge_counts)
    target_counts[badge] = current_level + 1
    try:
        items = purchase_level_items(target_counts, badge_data)
    except ValueError as exc:
        return {"state": "locked", "level": current_level + 1, "reason": str(exc)}
    for item in items:
        if item["badge"] == badge and item["level"] == current_level + 1:
            result = dict(item)
            result["state"] = "cost"
            return result
    return {"state": "locked", "level": current_level + 1, "reason": "Could not price next level."}


def badge_info_lines(badge, badge_data=None):
    badge = str(badge).lower()
    badge_data = badge_data or load_badge_data()
    badge_info = badge_data.get("badges", {}).get(badge, {})
    lines = [f"{badge.title()} Badge", ""]
    lines.append(f"Prerequisites: {prerequisite_text(badge)}")
    lines.append("")
    lines.append("Costs:")
    for level, numeral in ((1, "I"), (2, "II"), (3, "III"), (4, "IV")):
        lines.append(f"Level {numeral}: {format_kakera(badge_level_cost(badge, level, badge_data))}")
    perks = badge_info.get("perks", {})
    if perks:
        lines.append("")
        lines.append("Perks:")
        for text in perks.values():
            lines.append(text)
    discount = badge_info.get("discount")
    if discount:
        lines.append("")
        lines.append(f"Ruby IV discount: {discount.get('percent', 0)}% discount on other badges after Ruby IV is purchased.")
    return lines


def build_command_sequence(raw_user_id, raw_badge_counts):
    user_id = validate_user_id(raw_user_id)
    badge_counts = normalize_badge_counts(raw_badge_counts)
    errors = configuration_prerequisite_errors(badge_counts)
    if errors:
        raise ValueError("; ".join(errors))
    commands = [f"$kakerarefund <@{user_id}>", "confirm"]
    for badge, count in command_purchase_steps(badge_counts):
        commands.extend([f"${badge} {count}", "y"])
    return commands


def badge_count_sequence(raw_badge_counts):
    badge_counts = normalize_badge_counts(raw_badge_counts)
    return "".join(str(badge_counts[badge]) for badge in BADGES)


def format_set_result_message(config_name, raw_badge_counts):
    name = config_name.strip()
    if name:
        return f"Set to {name}"
    return f"Set to {badge_count_sequence(raw_badge_counts)}"


def find_matching_config_name(preferred_name, configs, raw_badge_counts):
    configs = configs if isinstance(configs, dict) else {}
    target_badges = normalize_badge_counts(raw_badge_counts)
    preferred_name = preferred_name.strip()
    if preferred_name in configs:
        preferred_config = normalize_config(configs[preferred_name])
        if preferred_config["badges"] == target_badges:
            return preferred_name
    for name in sorted(configs):
        config = normalize_config(configs[name])
        if config["badges"] == target_badges:
            return str(name)
    return ""


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
