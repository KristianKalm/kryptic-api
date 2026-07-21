import re

# Usernames are used directly as filesystem path segments (see
# get_user_data_path), so they must never contain path separators, "..",
# or other characters that could escape the per-user directory.
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def is_valid_username(username: str) -> bool:
    return isinstance(username, str) and USERNAME_PATTERN.fullmatch(username) is not None
