from typing import Optional


def resolve_display_name(
    display_name: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    email: str,
) -> str:
    account_name = (display_name or "").strip()
    if account_name:
        return account_name

    person_name = " ".join(part.strip() for part in (first_name, last_name) if part and part.strip())
    return person_name or email
