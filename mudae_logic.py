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


def build_command_sequence(raw_user_id, raw_badge_counts):
    user_id = validate_user_id(raw_user_id)
    badge_counts = normalize_badge_counts(raw_badge_counts)
    commands = [f"$kakerarefund <@{user_id}>", "confirm"]
    for badge in BADGES:
        for _ in range(badge_counts[badge]):
            commands.extend([f"${badge}", "y"])
    return commands


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
