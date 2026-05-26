BADGES = ("bronze", "silver", "gold", "sapphire", "ruby", "emerald", "diamond")
DEFAULT_DELAY = 0.8


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


def command_badge_order(badge_counts):
    if badge_counts.get("ruby") == 4:
        return ("ruby",) + tuple(badge for badge in BADGES if badge != "ruby")
    return BADGES


def build_command_sequence(raw_user_id, raw_badge_counts):
    user_id = validate_user_id(raw_user_id)
    badge_counts = normalize_badge_counts(raw_badge_counts)
    commands = [f"$kakerarefund <@{user_id}>", "confirm"]
    for badge in command_badge_order(badge_counts):
        count = badge_counts[badge]
        if count:
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
