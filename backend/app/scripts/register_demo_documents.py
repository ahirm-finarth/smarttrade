from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.services.demo_documents import register_demo_documents


def main():
    try:
        with Session(get_engine()) as session:
            counts = register_demo_documents(session, get_settings())
    except Exception:
        print("Demo registration failed. Check seeded cases, migration, and local storage.")
        raise SystemExit(1) from None
    print("Synthetic PDFs:", counts, "(registration does not call the LLM)")


if __name__ == "__main__":
    main()
