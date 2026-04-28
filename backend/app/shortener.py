import random
import string


_ALPHABET = string.ascii_letters + string.digits  # 62 chars → 62^7 ≈ 3.5 trillion combos


def generate_code(length: int = 7) -> str:
    return "".join(random.choices(_ALPHABET, k=length))


def is_valid_url(url: str) -> bool:
    return url.startswith(("http://", "https://"))
