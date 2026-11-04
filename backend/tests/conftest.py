import os
import sys

# Make `import config`, `import services.*` work when pytest runs from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import pytest  # noqa: E402


def pytest_collection_modifyitems(config, items):
    """Integration tests wipe the databases they talk to, so they are strictly opt-in."""
    if os.environ.get("RESEARCHOS_ALLOW_WIPE") == "1":
        return
    skip = pytest.mark.skip(reason="set RESEARCHOS_ALLOW_WIPE=1 with disposable WEAVIATE_URL / NEO4J_URI to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


def assert_disposable(settings):
    """Integration tests wipe their databases: never point them at the docker-compose stack."""
    for url in (settings.WEAVIATE_URL, settings.NEO4J_URI):
        host = url.split("//", 1)[-1].split(":", 1)[0]
        assert host not in ("weaviate", "neo4j"), f"refusing to wipe the compose database at {url}"
