from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

CITY_MAP = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "gurgaon": "Gurugram",
    "gurugram": "Gurugram",
    "pune": "Pune",
    "noida": "Noida",
    "delhi": "Delhi",
    "new delhi": "New Delhi",
    "delhi ncr": "Delhi NCR",
}

SKILL_MAP = {
    "n8n": "n8n",
    "web scraping": "Web Scraping",
    "fastapi": "FastAPI",
    "rest apis": "REST APIs",
    "mongodb": "MongoDB",
    "mysql": "MySQL",
    "sql": "SQL",
    "python": "Python",
    "javascript": "JavaScript",
    "react": "React",
    "docker": "Docker",
    "zapier": "Zapier",
    "langchain": "LangChain",
    "pandas": "Pandas",
    "selenium": "Selenium",
}

STATUS_MAP = {
    "active": "active",
    "inactive": "inactive",
    "paused": "paused",
}


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_name(value: object) -> str:
    return clean_text(value).casefold()


def normalize_email(value: object) -> str:
    return clean_text(value).casefold()


def normalize_phone(value: object) -> str:
    digits = re.sub(r"\D", "", clean_text(value))
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    elif len(digits) > 10:
        # Keep the last 10 digits for Indian numbers containing +91/91.
        digits = digits[-10:]
    return digits


def normalize_city(value: object) -> str:
    raw = clean_text(value).casefold()
    return CITY_MAP.get(raw, clean_text(value).title()) if raw else ""


def normalize_status(value: object) -> str:
    raw = clean_text(value).casefold()
    return STATUS_MAP.get(raw, raw)


def parse_bool(value: object) -> int | None:
    raw = clean_text(value).casefold()
    if raw in {"y", "yes", "true", "1"}:
        return 1
    if raw in {"n", "no", "false", "0"}:
        return 0
    return None


def normalize_skills(value: object) -> list[str]:
    raw = clean_text(value)
    if not raw:
        return []
    result: list[str] = []
    for item in raw.split(","):
        skill = clean_text(item).casefold()
        if not skill:
            continue
        canonical = SKILL_MAP.get(skill, clean_text(item))
        if canonical not in result:
            result.append(canonical)
    return result


def parse_date(value: object) -> str | None:
    raw = clean_text(value)
    if not raw:
        return None
    formats = ["%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Unsupported date format: {raw!r}")


def parse_number(value: object) -> float | None:
    raw = clean_text(value).replace(",", "")
    if not raw:
        return None
    try:
        return float(Decimal(raw))
    except InvalidOperation as exc:
        raise ValueError(f"Not a numeric value: {raw!r}") from exc


def normalize_ctc_inr(value: object) -> float | None:
    number = parse_number(value)
    if number is None:
        return None
    # Source 1 mixes raw INR-looking numbers and lakh-looking values.
    # Values below 100 are interpreted as lakhs; this assumption is documented.
    return number * 100_000 if number < 100 else number


def parse_rate(value: object) -> tuple[float | None, str | None]:
    raw = clean_text(value).casefold().replace(",", "")
    if not raw:
        return None, None
    if raw.endswith("/hr"):
        return parse_number(raw[:-3]), "hourly"
    if raw.endswith("/month"):
        amount_raw = raw[:-6]
        if amount_raw.endswith("k"):
            amount = parse_number(amount_raw[:-1])
            return (amount * 1000 if amount is not None else None), "monthly"
        amount = parse_number(amount_raw)
        return amount, "monthly"
    raise ValueError(f"Unsupported rate format: {value!r}")
