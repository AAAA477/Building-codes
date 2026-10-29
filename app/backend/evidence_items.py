"""Completeness hook for evidence files (called from completeness.compute)."""
from __future__ import annotations


def items(app: dict) -> list:
    try:
        import evidence
        recs = evidence.load_index(str(app.get("id") or ""))
    except Exception:
        return []
    out = []
    for i, d in enumerate(app.get("section_d") or []):
        did = d.get("id")
        files = [r for r in recs if r.get("doc_id") == did]
        nm = d.get("document_name") or did or f"Document {i + 1}"
        base = {"section": "D", "node_id": f"D.doc.{i}", "group": "documents"}
        blocked = [r for r in files if r.get("worst") == "block"]
        if blocked:
            why = next(c["message"] for c in blocked[0]["checks"] if c["level"] == "block")
            out.append({**base, "id": f"D.evidence.{i}", "label": f"Attached file: {nm}", "status": "missing",
                        "message": f"{blocked[0]['filename']} cannot be used. {why}", "priority": 1, "severity": "blocker"})
        elif not files and d.get("status") in ("provided", "to_be_prepared"):
            out.append({**base, "id": f"D.evidence.{i}", "label": f"Attached file: {nm}", "status": "uncertain",
                        "message": "No file is attached yet.", "priority": 4, "severity": "confirm"})
    return out
