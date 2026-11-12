def reply_key(text: str | None, *, is_text: bool, max_length: int) -> str:
    if not is_text:
        return "non_text"
    raw = (text or "").strip()
    if not raw:
        return "smalltalk"
    command = raw.split(maxsplit=1)[0].split("@", 1)[0].lower()
    if command == "/start":
        return "start"
    if command == "/help":
        return "help"
    if command == "/profile":
        return "profile"
    if command.startswith("/"):
        return "unknown_command"
    if len(raw) > max_length:
        return "too_long"
    return "smalltalk"
