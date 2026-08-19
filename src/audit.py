from pathlib import Path
import csv
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = PROJECT_ROOT / "consultbae.db"


FILES = {
    "naukri": DATA_DIR / "source1_naukri_applicants.csv",
    "gig_workers": DATA_DIR / "source2_gig_workers.csv",
    "cbnexus": DATA_DIR / "source3_cbnexus_contacts.csv",
}


def audit_csv(path):
    """Return total rows, blank rows, and non-blank rows."""
    total = 0
    blank = 0

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file)

        # Skip header
        next(reader, None)

        for row in reader:
            total += 1

            if not any(cell.strip() for cell in row):
                blank += 1

    return total, blank, total - blank


def get_database_counts(conn):
    """Get record counts from the database."""
    tables = {
        "people": "people",
        "source_records": "source_records",
        "applicants": "applicant_data",
        "gig_workers": "gig_worker_data",
        "cbnexus": "cbnexus_data",
    }

    counts = {}

    for label, table in tables.items():
        counts[label] = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

    return counts


def main():
    print("=== ConsultBae Data Audit ===")
    print()

    total_rows = 0
    total_blank = 0

    print("CSV audit:")

    for source, path in FILES.items():
        total, blank, meaningful = audit_csv(path)

        total_rows += total
        total_blank += blank

        print(f"  {source}:")
        print(f"    Total rows:      {total}")
        print(f"    Blank rows:      {blank}")
        print(f"    Meaningful rows: {meaningful}")

    print()
    print(f"Total physical rows:    {total_rows}")
    print(f"Total blank rows:       {total_blank}")
    print(f"Total meaningful rows:  {total_rows - total_blank}")

    print()

    conn = sqlite3.connect(DB_PATH)
    counts = get_database_counts(conn)

    print("Database counts:")
    for name, count in counts.items():
        print(f"  {name}: {count}")

    conn.close()


if __name__ == "__main__":
    main()