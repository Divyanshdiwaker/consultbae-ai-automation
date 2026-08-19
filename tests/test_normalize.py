from src.normalize import (
    normalize_city,
    normalize_ctc_inr,
    normalize_email,
    normalize_phone,
    normalize_skills,
    parse_date,
    parse_rate,
)


def test_phone_normalization():
    assert normalize_phone("+91-9000000254") == "9000000254"
    assert normalize_phone("919000000254") == "9000000254"
    assert normalize_phone("09000000254") == "9000000254"


def test_email_normalization():
    assert normalize_email(" ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG ") == "isha.chopra95@mailtest.example.org"


def test_city_normalization():
    assert normalize_city("GURGAON") == "Gurugram"
    assert normalize_city("bangalore") == "Bengaluru"
    assert normalize_city("PUNE") == "Pune"


def test_ctc_normalization():
    assert normalize_ctc_inr("4.2") == 420000
    assert normalize_ctc_inr("417964") == 417964


def test_rate_normalization():
    assert parse_rate("1415/hr") == (1415, "hourly")
    assert parse_rate("72k/month") == (72000, "monthly")


def test_date_normalization():
    assert parse_date("7 Jul 2026") == "2026-07-07"
    assert parse_date("2026-08-08") == "2026-08-08"


def test_skills_normalization():
    skills = normalize_skills("n8n, fastapi, mysql, python")
    assert skills == ["n8n", "FastAPI", "MySQL", "Python"]
