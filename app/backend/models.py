"""Pydantic models matching app/CONTRACT.md plus JSON-file persistence."""
from __future__ import annotations
import copy, json, uuid
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

BASE = Path(__file__).resolve().parent
DATA = BASE.parent / "data"
STORE_DIR = DATA / "store"
SAMPLES_DIR = DATA / "samples"
CONTENT_DIR = DATA / "content"
EDITION = "NBC(AE) 2023"
PROVENANCE_SOURCES = ("applicant", "lookup", "ai_draft", "needs_professional")


class _M(BaseModel):
    model_config = ConfigDict(extra="allow")


class Applicant(_M):
    owner_name: str = ""
    owner_representative: str = ""
    mailing_address: str = ""
    email: str = ""
    date_of_request: str = ""


class Project(_M):
    description: str = ""
    occupancy: str = ""
    storeys: Optional[int] = None
    building_area_m2: Optional[float] = None
    units_per_floor: Optional[int] = None
    sprinklered: Optional[bool] = None
    new_or_renovation: str = ""  # blank until the applicant answers; never assume 'new'
    part: Optional[str] = None


class Location(_M):
    jurisdiction_wide: bool = False
    permit_number: str = ""
    municipal_address: str = ""
    lot: str = ""
    block: str = ""
    plan: str = ""
    qtr: str = ""
    sec: str = ""
    twp: str = ""
    rge: str = ""
    mer: str = ""


class Mitigation(_M):
    id: str = ""
    label: str = ""
    detail: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class AcceptableSolution(_M):
    articles: list[str] = Field(default_factory=list)
    explanation: str = ""


class ProposedAlternative(_M):
    summary: str = ""
    mitigations: list[Mitigation] = Field(default_factory=list)


class SectionCRow(_M):
    article: str = ""
    objective: str = ""
    function: str = ""
    intent: str = ""
    explainer: str = ""
    source: dict = Field(default_factory=dict)
    verified: bool = False
    provenance: str = "lookup"


class Variance(_M):
    topic: str = ""  # unset until the applicant picks one or classify infers it from their description
    code_or_standard: str = ""
    acceptable_solution: AcceptableSolution = Field(default_factory=AcceptableSolution)
    proposed_alternative: ProposedAlternative = Field(default_factory=ProposedAlternative)
    section_c: list[SectionCRow] = Field(default_factory=list)


class SectionDItem(_M):
    id: str = ""
    document_name: str = ""
    responsible_party: str = ""
    professional_required: bool = False
    status: str = "missing"  # provided|missing|to_be_prepared
    date: str = ""


class ProfessionalFlag(_M):
    id: str
    reason: str
    article_refs: list[str] = Field(default_factory=list)
    stop: bool = True


class Declarations(_M):
    privacy_consent: bool = False
    equal_or_better_ack: bool = False
    owner_signed: bool = False
    rep_signed: bool = False


class ProvenanceEntry(_M):
    source: str
    confidence: float = 1.0


class CompletenessItem(_M):
    id: str
    label: str
    section: str
    status: str
    message: str = ""
    node_id: str = ""


class Completeness(_M):
    percent: int = 0
    items: list[CompletenessItem] = Field(default_factory=list)


class Application(_M):
    id: str
    jurisdiction: str = "scc"
    edition: str = EDITION
    applicant: Applicant = Field(default_factory=Applicant)
    project: Project = Field(default_factory=Project)
    location: Location = Field(default_factory=Location)
    variance: Variance = Field(default_factory=Variance)
    section_d: list[SectionDItem] = Field(default_factory=list)
    professional_flags: list[ProfessionalFlag] = Field(default_factory=list)
    declarations: Declarations = Field(default_factory=Declarations)
    provenance: dict[str, ProvenanceEntry] = Field(default_factory=dict)
    completeness: Completeness = Field(default_factory=Completeness)


def deep_merge(base: dict, patch: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def new_application(**over) -> dict:
    d = Application(id=over.pop("id", uuid.uuid4().hex[:8])).model_dump()
    return deep_merge(d, over) if over else d


def _drop_none(x):
    if isinstance(x, dict):
        return {k: _drop_none(v) for k, v in x.items() if v is not None}
    if isinstance(x, list):
        return [_drop_none(v) for v in x]
    return x


def normalize(d: dict) -> dict:
    """Validate through the model (fills missing keys); keeps unknown keys."""
    d = _drop_none({k: v for k, v in d.items() if not k.startswith("_")})
    return Application.model_validate(d).model_dump()


def leaf_paths(patch: dict, prefix: str = "") -> list[str]:
    paths = []
    for k, v in patch.items():
        p = f"{prefix}{k}"
        if isinstance(v, dict) and v:
            paths += leaf_paths(v, p + ".")
        else:
            paths.append(p)
    return paths


def get_path(d: Any, path: str, default=None):
    cur = d
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return default
    return cur


def set_path(d: dict, path: str, value) -> None:
    parts = path.split(".")
    cur = d
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


# ---- persistence -------------------------------------------------------
_MEM: dict[str, dict] = {}


def save(app: dict) -> dict:
    _MEM[app["id"]] = app
    try:
        STORE_DIR.mkdir(parents=True, exist_ok=True)
        (STORE_DIR / f"{app['id']}.json").write_text(json.dumps(app, indent=2), encoding="utf-8")
    except OSError:
        pass
    return app


def load(app_id: str) -> Optional[dict]:
    if app_id in _MEM:
        return _MEM[app_id]
    f = STORE_DIR / f"{Path(app_id).name}.json"
    if f.exists():
        try:
            _MEM[app_id] = json.loads(f.read_text(encoding="utf-8"))
            return _MEM[app_id]
        except (OSError, ValueError):
            return None
    return None
