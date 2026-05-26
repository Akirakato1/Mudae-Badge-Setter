import json
from pathlib import Path


BADGES = ("bronze", "silver", "gold", "sapphire", "ruby", "emerald", "diamond")
DEFAULT_DELAY = 0.8
BASIC_UNLOCK_BADGES = ("bronze", "silver", "gold")
LEVEL_FOUR_UNLOCK_BADGES = ("ruby", "sapphire")
TWO_LEVEL_FOUR_UNLOCK_BADGES = ("emerald", "diamond")
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
      "prerequisites": [
        {
          "any_two_level_4_badges": true
        }
      ]
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
        "bronze": 2,
        "gold": 2,
        "sapphire": 4,
        "silver": 2
      },
      "estimated_cost": 68000,
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


def load_badge_data(path=None):
    if path is None:
        path = Path(__file__).resolve().with_name(BADGE_DATA_FILENAME)
    try:
        with Path(path).open("r", encoding="utf-8") as file:
            return json.load(file)
    except OSError:
        return json.loads(EMBEDDED_BADGE_DATA_JSON)


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

    def buy_basic_unlocks():
        for badge in BASIC_UNLOCK_BADGES:
            buy_to_level(badge, 2)

    def has_basic_unlocks():
        return all(owned[badge] >= 2 for badge in BASIC_UNLOCK_BADGES)

    def can_buy_basic_unlocks():
        return all(badge_counts[badge] >= 2 for badge in BASIC_UNLOCK_BADGES)

    def unlock_basic_or_two_level_four(badge):
        if has_basic_unlocks() or level_four_count((badge,)) >= 2:
            return
        if can_buy_basic_unlocks():
            buy_basic_unlocks()
        else:
            buy_level_four_unlocks((badge,))

    if badge_counts["ruby"] == 4:
        unlock_basic_or_two_level_four("ruby")
        buy_to_level("ruby", 4)

    for badge in BADGES:
        if not remaining[badge]:
            continue
        if badge in LEVEL_FOUR_UNLOCK_BADGES:
            unlock_basic_or_two_level_four(badge)
        elif badge in TWO_LEVEL_FOUR_UNLOCK_BADGES and level_four_count((badge,)) < 2:
            buy_level_four_unlocks((badge,))
        buy(badge, remaining[badge])

    return steps


def build_command_sequence(raw_user_id, raw_badge_counts):
    user_id = validate_user_id(raw_user_id)
    badge_counts = normalize_badge_counts(raw_badge_counts)
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
