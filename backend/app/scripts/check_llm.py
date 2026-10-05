import json

from app.core.config import get_settings
from app.integrations.llm.client import LLMClient, LLMUnavailable


def main():
    client = None
    try:
        client = LLMClient(get_settings())
        print(json.dumps(client.healthcheck()))
    except LLMUnavailable as exc:
        print(str(exc))
        raise SystemExit(1) from None
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    main()
