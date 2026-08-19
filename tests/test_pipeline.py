import sqlite3
from pathlib import Path

from src.ingest import run_ingestion


def test_pipeline_builds_expected_database(tmp_path: Path):
    data_dir = Path(__file__).parents[1] / "data"
    db_path = tmp_path / "consultbae.db"
    run_ingestion(data_dir, db_path)

    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM people").fetchone()[0] == 60
    assert conn.execute("SELECT COUNT(*) FROM applicant_data").fetchone()[0] == 40
    assert conn.execute("SELECT COUNT(*) FROM gig_worker_data").fetchone()[0] == 30
    assert conn.execute("SELECT COUNT(*) FROM cbnexus_data").fetchone()[0] == 30

    # The malformed Isha row is recovered and maps to the existing Isha person.
    assert conn.execute(
        "SELECT COUNT(*) FROM people WHERE normalized_email=?",
        ("isha.chopra95@mailtest.example.org",),
    ).fetchone()[0] == 1

    # Same name, conflicting identity information: keep Arjun Mehta records separate.
    assert conn.execute(
        "SELECT COUNT(*) FROM people WHERE normalized_name=?",
        ("arjun mehta",),
    ).fetchone()[0] == 3

    # Repeated header in CBNexus is rejected rather than inserted as a person.
    assert conn.execute(
        "SELECT COUNT(*) FROM source_records WHERE source_name='cbnexus' AND match_method='rejected'"
    ).fetchone()[0] == 1
