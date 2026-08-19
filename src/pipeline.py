from __future__ import annotations

import argparse
from pathlib import Path

from .ingest import run_ingestion


def main() -> None:
    parser = argparse.ArgumentParser(description="ConsultBae data ingestion pipeline")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--db", type=Path, default=Path("consultbae.db"))
    args = parser.parse_args()
    run_ingestion(args.data_dir, args.db)
    print(f"Database created: {args.db}")


if __name__ == "__main__":
    main()
