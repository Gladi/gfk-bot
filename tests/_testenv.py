"""Testumgebung: eigene Wegwerf-DB, Paketpfad. Wird von jedem Test zuerst importiert."""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bot-core"))      # Git-Submodul botcore
os.environ["GFK_DB_FILE"] = os.path.join(tempfile.mkdtemp(prefix="gfk_test_"), "gfk.db")
