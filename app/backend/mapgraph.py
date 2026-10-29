"""Mind-map nodes/edges from completeness. Colours (frontend): complete=green, uncertain=amber,
missing=red, needs_professional=purple, lookup=blue."""
from __future__ import annotations
from models import get_path

SECTIONS = [("A", "A. Applicant"), ("B", "B. Project and location"),
            ("C", "C. Code variance"), ("D", "D. Supporting documents"), ("SIGN", "Declarations")]
ORDER = ["missing", "needs_professional", "uncertain", "complete"]

PROV_PATH = {
    "C.code_or_standard": "variance.code_or_standard", "C.articles": "variance.acceptable_solution.articles",
    "C.explanation": "variance.acceptable_solution.explanation", "C.alternative": "variance.proposed_alternative.summary",
    "C.mitigations": "variance.proposed_alternative.mitigations",
    "B.location": "location.municipal_address", "B.permit_number": "location.permit_number",
}


def _prov(app, item):
    pv = app.get("provenance", {})
    iid = item["id"]
    path = PROV_PATH.get(iid)
    if not path:
        sec, _, k = iid.partition(".")
        path = {"A": "applicant.", "B": "project."}.get(sec, "") + k
    if iid.startswith("C.row."):
        return "lookup"
    if iid == "D.professional":
        return "needs_professional"
    e = pv.get(path)
    return e.get("source") if isinstance(e, dict) else None


def build(app: dict, completeness: dict) -> dict:
    items = completeness["items"]
    nodes = [{"id": "root", "label": "Application", "section": "ROOT", "status": "uncertain",
              "provenance": None, "data": {"percent": completeness["percent"]}}]
    edges = []
    root_status = []
    for sec, label in SECTIONS:
        its = [i for i in items if i["section"] == sec]
        if not its:
            continue
        sts = [i["status"] for i in its]
        st = next((s for s in ORDER if s in sts), "complete")
        root_status.append(st)
        sid = f"sec.{sec}"
        nodes.append({"id": sid, "label": label, "section": sec, "status": st, "provenance": None,
                      "data": {"complete": sts.count("complete"), "total": len(sts)}})
        edges.append({"source": "root", "target": sid})
        for it in its:
            prov = _prov(app, it)
            status = it["status"]
            if it["id"].startswith("C.row.") and status == "complete" and prov == "lookup":
                status = "lookup"
            nid = it["node_id"] or it["id"]
            data = {"message": it["message"]}
            if it["id"].startswith("C.row."):
                data["row"] = get_path(app, f"variance.section_c.{it['id'].split('.')[-1]}")
            nodes.append({"id": nid, "label": it["label"], "section": sec, "status": status,
                          "provenance": prov, "data": data})
            edges.append({"source": sid, "target": nid})
    nodes[0]["status"] = next((s for s in ORDER if s in root_status), "complete")
    return {"nodes": nodes, "edges": edges}
