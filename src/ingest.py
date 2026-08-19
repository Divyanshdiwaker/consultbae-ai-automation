from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Iterable

from .database import connect, initialize_database
from .normalize import (
    clean_text,
    normalize_city,
    normalize_ctc_inr,
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_skills,
    normalize_status,
    parse_bool,
    parse_date,
    parse_number,
    parse_rate,
)


def re_name_like(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z .'-]+", value)) and "@" not in value


class IngestError(Exception):
    pass


def read_csv_rows(path: Path) -> Iterable[tuple[int, dict[str, str], list[str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = len(reader.fieldnames or [])
        for row_number, row in enumerate(reader, start=2):
            raw_values = [value or "" for value in row.values()]
            flags: list[str] = []
            if not any(clean_text(v) for v in raw_values):
                flags.append("blank_row")
                yield row_number, row, flags
                continue
            # DictReader stores extra CSV fields under None.
            if None in row:
                flags.append("malformed_column_count")
            if len(raw_values) != expected:
                flags.append("column_count_mismatch")
            yield row_number, row, flags


def insert_person(conn, record: dict) -> int:
    conn.execute(
        """
        INSERT INTO people
        (full_name, normalized_name, email, normalized_email, phone,
         normalized_phone, city, normalized_city)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["full_name"], record["normalized_name"], record["email"],
            record["normalized_email"], record["phone"], record["normalized_phone"],
            record["city"], record["normalized_city"],
        ),
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def upsert_source_record(
    conn,
    person_id: int | None,
    source: str,
    row_number: int,
    raw_data: dict,
    method: str,
    confidence: float,
    flags: list[str],
) -> None:
    conn.execute(
        """
        DELETE FROM source_records
        WHERE source_name = ?
          AND source_row_number = ?
        """,
        (source, row_number),
    )

    conn.execute(
        """
        INSERT INTO source_records
        (
            person_id,
            source_name,
            source_row_number,
            raw_data,
            match_method,
            match_confidence,
            data_quality_flags
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            person_id,
            source,
            row_number,
            json.dumps(raw_data, ensure_ascii=False),
            method,
            confidence,
            json.dumps(flags),
        ),
    )


def find_person(conn, normalized_email: str, normalized_phone: str) -> tuple[int | None, str, float]:
    if normalized_email:
        row = conn.execute(
            "SELECT person_id FROM people WHERE normalized_email = ?",
            (normalized_email,),
        ).fetchone()
        if row:
            return row[0], "exact_email", 1.0
    if normalized_phone:
        row = conn.execute(
            "SELECT person_id FROM people WHERE normalized_phone = ?",
            (normalized_phone,),
        ).fetchone()
        if row:
            return row[0], "exact_phone", 0.99
    return None, "new_person", 0.0


def ensure_person(conn, full_name: str, email: str, phone: str, city: str) -> tuple[int, str, float]:
    normalized_email = normalize_email(email)
    normalized_phone = normalize_phone(phone)
    person_id, method, confidence = find_person(conn, normalized_email, normalized_phone)
    if person_id is not None:
        # Prefer a more complete name/city from a later source when the identity
        # match is exact. Never replace an existing value with an empty value.
        existing = conn.execute(
            "SELECT full_name, city FROM people WHERE person_id = ?", (person_id,)
        ).fetchone()
        existing_name = existing[0] or ""
        existing_city = existing[1] or ""
        if len(clean_text(full_name)) > len(clean_text(existing_name)):
            conn.execute(
                "UPDATE people SET full_name=?, normalized_name=?, updated_at=CURRENT_TIMESTAMP WHERE person_id=?",
                (full_name, normalize_name(full_name), person_id),
            )
        if not existing_city and city:
            conn.execute(
                "UPDATE people SET city=?, normalized_city=?, updated_at=CURRENT_TIMESTAMP WHERE person_id=?",
                (city, normalize_city(city), person_id),
            )
        return person_id, method, confidence
    record = {
        "full_name": full_name,
        "normalized_name": normalize_name(full_name),
        "email": email,
        "normalized_email": normalized_email,
        "phone": phone,
        "normalized_phone": normalized_phone,
        "city": city,
        "normalized_city": normalize_city(city),
    }
    return insert_person(conn, record), "new_person", 0.0


def ingest_naukri(conn, path: Path) -> None:
    for row_number, row, flags in read_csv_rows(path):
        if "blank_row" in flags:
            continue
        full_name = clean_text(row.get("Full Name"))
        email = clean_text(row.get("Email"))
        phone = clean_text(row.get("Phone"))
        city = clean_text(row.get("City"))
        person_id, method, confidence = ensure_person(conn, full_name, email, phone, city)
        if method != "new_person":
            flags.append("duplicate_person_across_sources")
        conn.execute(
            """
            INSERT INTO applicant_data
            (person_id, experience_years, current_ctc_inr, applied_date, skills)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(person_id) DO UPDATE SET
                experience_years=excluded.experience_years,
                current_ctc_inr=excluded.current_ctc_inr,
                applied_date=excluded.applied_date,
                skills=excluded.skills
            """,
            (person_id, parse_number(row.get("Experience (Years)")),
             normalize_ctc_inr(row.get("Current CTC")),
             parse_date(row.get("Applied Date")),
             json.dumps(normalize_skills(row.get("Skills")), ensure_ascii=False)),
        )
        upsert_source_record(conn, person_id, "naukri", row_number, dict(row), method, confidence, flags)


def ingest_gig(conn, path: Path) -> None:
    for row_number, row, flags in read_csv_rows(path):
        if "blank_row" in flags:
            flags.append("blank_source_record")
            continue

        # One source-2 row is semantically shifted even though it has the expected
        # number of CSV columns: the skills list is in email_id, the email is in
        # worker_name, the name is in rate, etc. Detect and recover that row.
        first = clean_text(row.get("email_id"))
        looks_like_shifted_isha = (
            "," in first
            and "@" in clean_text(row.get("worker_name"))
            and re_name_like(clean_text(row.get("rate")))
            and "/hr" in clean_text(row.get("location"))
            and clean_text(row.get("status")).casefold() in {"pune", "noida", "delhi", "gurgaon", "gurugram", "bangalore", "bengaluru", "new delhi"}
        )
        if looks_like_shifted_isha:
            flags.extend(["malformed_field_alignment", "recovered_shifted_row"])
            email = clean_text(row.get("worker_name"))
            full_name = clean_text(row.get("rate"))
            rate = clean_text(row.get("location"))
            location = clean_text(row.get("status"))
            status = clean_text(row.get("skill_tags"))
            skills = first
        else:
            email = clean_text(row.get("email_id"))
            full_name = clean_text(row.get("worker_name"))
            rate = clean_text(row.get("rate"))
            location = clean_text(row.get("location"))
            status = clean_text(row.get("status"))
            skills = clean_text(row.get("skill_tags"))

        person_id, method, confidence = ensure_person(conn, full_name, email, "", location)
        if method != "new_person":
            flags.append("duplicate_person_across_sources")
        amount, unit = parse_rate(rate)
        conn.execute(
            """
            INSERT INTO gig_worker_data
            (person_id, rate_amount, rate_unit, status, skill_tags)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(person_id) DO UPDATE SET
                rate_amount=excluded.rate_amount,
                rate_unit=excluded.rate_unit,
                status=excluded.status,
                skill_tags=excluded.skill_tags
            """,
            (person_id, amount, unit, normalize_status(status),
             json.dumps(normalize_skills(skills), ensure_ascii=False)),
        )
        upsert_source_record(conn, person_id, "gig_workers", row_number, dict(row), method, confidence, flags)


def ingest_cbnexus(conn, path: Path) -> None:
    for row_number, row, flags in read_csv_rows(path):
        if "blank_row" in flags:
            continue
        # A repeated header appears inside the data.
        if clean_text(row.get("Name")).casefold() == "name":
            flags.append("repeated_header_row")
            upsert_source_record(conn, None, "cbnexus", row_number, dict(row), "rejected", 0.0, flags)
            continue
        full_name = clean_text(row.get("Name"))
        phone = clean_text(row.get("Phone Number"))
        city = clean_text(row.get("City"))
        person_id, method, confidence = ensure_person(conn, full_name, "", phone, city)
        if method != "new_person":
            flags.append("duplicate_person_across_sources")
        conn.execute(
            """
            INSERT INTO cbnexus_data
            (person_id, verified, projects_completed)
            VALUES (?, ?, ?)
            ON CONFLICT(person_id) DO UPDATE SET
                verified=excluded.verified,
                projects_completed=excluded.projects_completed
            """,
            (person_id, parse_bool(row.get("Verified")),
             int(parse_number(row.get("Projects Completed"))) if clean_text(row.get("Projects Completed")) else None),
        )
        upsert_source_record(conn, person_id, "cbnexus", row_number, dict(row), method, confidence, flags)


def run_ingestion(data_dir: Path, db_path: Path) -> None:
    initialize_database(db_path)
    with connect(db_path) as conn:
        ingest_naukri(conn, data_dir / "source1_naukri_applicants.csv")
        ingest_gig(conn, data_dir / "source2_gig_workers.csv")
        ingest_cbnexus(conn, data_dir / "source3_cbnexus_contacts.csv")
