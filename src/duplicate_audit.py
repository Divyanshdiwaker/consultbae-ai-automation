from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "consultbae.db"


def find_same_source_duplicates(conn):
    return conn.execute(
        """
        SELECT
            sr.source_name,
            sr.person_id,
            p.full_name,
            COUNT(*) AS record_count,
            GROUP_CONCAT(sr.source_row_number, ', ') AS source_rows
        FROM source_records AS sr
        LEFT JOIN people AS p
            ON sr.person_id = p.person_id
        WHERE sr.person_id IS NOT NULL
        GROUP BY sr.source_name, sr.person_id, p.full_name
        HAVING COUNT(*) > 1
        ORDER BY sr.source_name, sr.person_id
        """
    ).fetchall()


def get_duplicate_details(conn, source, person_id):
    return conn.execute(
        """
        SELECT
            source_row_number,
            match_method,
            match_confidence,
            data_quality_flags
        FROM source_records
        WHERE source_name = ?
          AND person_id = ?
        ORDER BY source_row_number
        """,
        (source, person_id),
    ).fetchall()


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    print("=== ConsultBae Same-Source Duplicate Audit ===")
    print()

    duplicate_groups = find_same_source_duplicates(conn)

    if not duplicate_groups:
        print("No same-source duplicates found.")
        conn.close()
        return

    for (
        source,
        person_id,
        name,
        record_count,
        source_rows,
    ) in duplicate_groups:

        print(
            f"{source} | "
            f"Person {person_id} | "
            f"{name}"
        )

        print(
            f"  Duplicate records: {record_count}"
        )

        print(
            f"  Source rows: {source_rows}"
        )

        details = get_duplicate_details(
            conn,
            source,
            person_id,
        )

        for (
            row_number,
            method,
            confidence,
            flags,
        ) in details:

            print(
                f"    row {row_number} | "
                f"{method} | "
                f"confidence={confidence} | "
                f"flags={flags}"
            )

        print()

    print(
        f"Duplicate groups found: "
        f"{len(duplicate_groups)}"
    )

    conn.close()


if __name__ == "__main__":
    main()