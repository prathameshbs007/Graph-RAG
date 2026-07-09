import os
import tempfile

# Must run before any test module imports application code, since config.py
# reads these as required settings at import time.
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("NEO4J_PASSWORD", "test-neo4j-password")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("FIGURES_DIR", os.path.join(tempfile.gettempdir(), "researchos_test_figures"))
