from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from .normalize import normalize_email, normalize_phone, normalize_name


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "consultbae.db"

app = FastAPI(
    title="ConsultBae Automation API",
    version="1.0.0",
)


def find_person(email: str = "", phone: str = ""):
    normalized_email = normalize_email(email)
    normalized_phone = normalize_phone(phone)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        if normalized_email:
            row = conn.execute(
                """
                SELECT
                    person_id,
                    full_name,
                    email,
                    phone,
                    city
                FROM people
                WHERE normalized_email = ?
                LIMIT 1
                """,
                (normalized_email,),
            ).fetchone()

            if row:
                return {
                    "found": True,
                    "match_method": "exact_email",
                    "confidence": 1.0,
                    "person": dict(row),
                }

        if normalized_phone:
            row = conn.execute(
                """
                SELECT
                    person_id,
                    full_name,
                    email,
                    phone,
                    city
                FROM people
                WHERE normalized_phone = ?
                LIMIT 1
                """,
                (normalized_phone,),
            ).fetchone()

            if row:
                return {
                    "found": True,
                    "match_method": "exact_phone",
                    "confidence": 0.99,
                    "person": dict(row),
                }

        return {
            "found": False,
            "match_method": "new_person",
            "confidence": 0.0,
            "person": None,
        }

    finally:
        conn.close()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "database_exists": DB_PATH.exists(),
    }


@app.get("/people/lookup")
def people_lookup(
    email: str = Query(default=""),
    phone: str = Query(default=""),
):
    try:
        return find_person(email=email, phone=phone)

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "found": False,
                "error": str(exc),
            },
        )


@app.post("/people")
def create_person(payload: dict):
    full_name = str(payload.get("full_name", "")).strip()
    email = str(payload.get("email", "")).strip()
    phone = str(payload.get("phone", "")).strip()
    city = str(payload.get("city", "")).strip()

    if not full_name:
        return JSONResponse(
            status_code=400,
            content={"error": "full_name is required"},
        )

    normalized_name = normalize_name(full_name)
    normalized_email = normalize_email(email)
    normalized_phone = normalize_phone(phone)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # Prevent accidental duplicate creation by email.
        if normalized_email:
            existing = conn.execute(
                """
                SELECT person_id, full_name, email, phone, city
                FROM people
                WHERE normalized_email = ?
                LIMIT 1
                """,
                (normalized_email,),
            ).fetchone()

            if existing:
                return {
                    "created": False,
                    "reason": "already_exists",
                    "person": dict(existing),
                }

        # Prevent accidental duplicate creation by phone.
        if normalized_phone:
            existing = conn.execute(
                """
                SELECT person_id, full_name, email, phone, city
                FROM people
                WHERE normalized_phone = ?
                LIMIT 1
                """,
                (normalized_phone,),
            ).fetchone()

            if existing:
                return {
                    "created": False,
                    "reason": "already_exists",
                    "person": dict(existing),
                }

        cursor = conn.execute(
            """
            INSERT INTO people (
                full_name,
                normalized_name,
                email,
                phone,
                city,
                normalized_email,
                normalized_phone
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                full_name,
                normalized_name,
                email,
                phone,
                city,
                normalized_email,
                normalized_phone,
            ),
        )

        conn.commit()

        person_id = cursor.lastrowid

        row = conn.execute(
            """
            SELECT person_id, full_name, email, phone, city
            FROM people
            WHERE person_id = ?
            """,
            (person_id,),
        ).fetchone()

        return {
            "created": True,
            "person": dict(row),
        }

    except Exception as exc:
        conn.rollback()

        return JSONResponse(
            status_code=500,
            content={
                "created": False,
                "error": str(exc),
            },
        )

    finally:
        conn.close()