"""Corpus stream: NBC(AE) 2023 extraction, citation verifier and search. Real data only."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # repo root ("Building codes")
FILES = ROOT / "files"
DATA = ROOT / "app" / "data" / "corpus"
EDITION = "NBC(AE) 2023"
