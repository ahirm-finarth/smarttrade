import argparse
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import ROOT
from app.db.session import get_engine
from app.services.demo_import import SourceError, ingest, read_sources


def main():
    parser = argparse.ArgumentParser(
        description="Import supplied synthetic Smart Trade reference data"
    )
    parser.add_argument("--source", type=Path, default=ROOT / "data/raw")
    args = parser.parse_args()
    try:
        bundle = read_sources(args.source)
        with Session(get_engine()) as session, session.begin():
            counts = ingest(session, bundle)
    except SourceError as exc:
        print(str(exc))
        raise SystemExit(1) from None
    except Exception:
        print("Import failed; transaction rolled back. Check connectivity and migration status.")
        raise SystemExit(1) from None
    print("Smart Trade synthetic demo seed complete")
    for name, count in counts.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
