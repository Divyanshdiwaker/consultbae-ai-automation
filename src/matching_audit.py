from __future__ import annotations

import json
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "consultbae.db"


def get_matching_summary(conn):
    return conn.execute(
        """
        SELECT
            match_method,
            COUNT(*) AS record_count
        FROM source_records
        GROUP BY match_method
        ORDER BY match_method
        """
    ).fetchall()


def get_merged_records(conn):
    return conn.execute(
        """
        SELECT
            sr.person_id,
            p.full_name,
            sr.source_name,
            sr.source_row_number,
            sr.match_method,
            sr.match_confidence
        FROM source_records AS sr
        LEFT JOIN people AS p
            ON sr.person_id = p.person_id
        WHERE sr.match_method NOT IN ('new_person', 'rejected')
        ORDER BY sr.person_id, sr.source_name, sr.source_row_number
        """
    ).fetchall()


def get_people_with_multiple_sources(conn):
    return conn.execute(
        """
        SELECT
            p.person_id,
            p.full_name,
            COUNT(DISTINCT sr.source_name) AS source_count
        FROM people AS p
        JOIN source_records AS sr
            ON p.person_id = sr.person_id
        WHERE sr.person_id IS NOT NULL
        GROUP BY p.person_id, p.full_name
        HAVING COUNT(DISTINCT sr.source_name) > 1
        ORDER BY p.person_id
        """
    ).fetchall()


def get_data_quality_flags(conn):
    return conn.execute(
        """
        SELECT
            source_name,
            data_quality_flags,
            COUNT(*) AS record_count
        FROM source_records
        WHERE data_quality_flags != '[]'
        GROUP BY source_name, data_quality_flags
        ORDER BY source_name
        """
    ).fetchall()


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    print("=== ConsultBae Matching Audit ===")
    print()

    print("1. Matching summary")
    print("-" * 50)

    for method, count in get_matching_summary(conn):
        print(f"{method}: {count}")

    print()

    print("2. People matched across multiple sources")
    print("-" * 50)

    multi_source_people = get_people_with_multiple_sources(conn)

    for person_id, name, source_count in multi_source_people:
        print(
            f"Person {person_id}: {name} "
            f"({source_count} sources)"
        )

    print(
        f"\nTotal people appearing in multiple sources: "
        f"{len(multi_source_people)}"
    )

    print()

    print("3. Individual merged records")
    print("-" * 50)

    merged_records = get_merged_records(conn)

    for (
        person_id,
        name,
        source,
        row_number,
        method,
        confidence,
    ) in merged_records:
        print(
            f"Person {person_id} | "
            f"{name} | "
            f"{source} row {row_number} | "
            f"{method} | "
            f"confidence={confidence}"
        )

    print()

    print("4. Data-quality flags")
    print("-" * 50)

    flags = get_data_quality_flags(conn)

    if not flags:
        print("No data-quality flags found.")
    else:
        for source, flag_json, count in flags:
            try:
                flag_list = json.loads(flag_json)
            except json.JSONDecodeError:
                flag_list = [flag_json]

            print(
                f"{source}: "
                f"{flag_list} "
                f"({count} record(s))"
            )

    conn.close()


if __name__ == "__main__":
    main()