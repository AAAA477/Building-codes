"""Submission package: filled form(s) + attachments + cover note + prefilled email DRAFT (never sent)."""
import os
import tempfile
import zipfile
import mimetypes
import reviewer
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formatdate

from .fill_scc import fill_scc
from .calgary_overlay import fill_calgary

RECIPIENTS = {
    "scc": ("accreditation@safetycodes.ab.ca", "From the header text of the official SCC variance form (Administrator of Accreditation)."),
    "calgary": ("[assigned Safety Codes Officer, see permit file]", "Calgary guide: submit by email to the assigned Safety Codes Officer."),
    "edmonton": ("[plans examiner assigned to your building permit file]",
                 "UNCONFIRMED: no Edmonton-specific variance form or submission address was found in the source files."),
}


def _check_signed(app):
    d = app.get("declarations") or {}
    if d.get("owner_signed") is not True:
        raise ValueError("Cannot build submission package: declarations.owner_signed is not true. "
                         "The owner must sign the form and a person must confirm it before the package unlocks.")
    rep = ((app.get("applicant") or {}).get("owner_representative") or "").strip()
    rep_named = bool(rep) and not (rep.startswith("[") and rep.endswith("]"))  # '[to be completed...]' is not a name
    if rep_named and d.get("rep_signed") is not True:
        raise ValueError("Cannot build submission package: an owner's representative is named but declarations.rep_signed is not true.")


def _variance_lines(app) -> list:
    """Name the STANDATA variance relied on only when every condition is confirmed; attribute borrowed conditions."""
    out = []
    rel = reviewer._relied(app)
    if rel and rel["total"] and rel["unmet"] == 0:
        out += [f"## Relied-on variance", f"- Relies on STANDATA {rel['number']} ({rel['edition']}): all {rel['total']} conditions confirmed by the applicant. "
                "Whether it applies is for the authority having jurisdiction to decide.", ""]
    borrowed = [m for m in ((app.get("variance") or {}).get("proposed_alternative") or {}).get("mitigations", []) if str(m.get("id", "")).startswith("V-")]
    if borrowed:
        out += ["## Alternative drawn from STANDATA (accepted by the applicant)"] + [f"- {m.get('label')}: {m.get('detail')}" for m in borrowed] + [""]
    return out


def _cover_note(app, enclosed, jur, to_addr, to_note, warnings):
    ap, pr, loc, var = (app.get(k) or {} for k in ("applicant", "project", "location", "variance"))
    L = [f"# Cover note: variance request ({app.get('id', '')})", "",
         "> DRAFT prepared with a completeness-checking tool. It is not a determination of safety or equivalence, "
         "and nothing has been sent. A person must review, attach and send.", "",
         "## Applicant",
         f"- Owner: {ap.get('owner_name') or '[not provided]'}",
         f"- Owner's representative: {ap.get('owner_representative') or '[none]'}",
         f"- Mailing address: {ap.get('mailing_address') or '[not provided]'}",
         f"- Email: {ap.get('email') or '[not provided]'}",
         f"- Date of request: {ap.get('date_of_request') or '[not provided]'}", "",
         "## Project summary",
         f"- Description: {pr.get('description') or '[not provided]'}",
         f"- Location: {loc.get('municipal_address') or '[not provided]'}; permit: {loc.get('permit_number') or '[not provided]'}",
         f"- Code or standard varied: {var.get('code_or_standard') or '[not provided]'} ({app.get('edition', '')})",
         f"- Provisions: {', '.join((var.get('acceptable_solution') or {}).get('articles') or []) or '[not provided]'}",
         f"- Proposed alternative: {(var.get('proposed_alternative') or {}).get('summary') or '[not provided]'}", "",
         *_variance_lines(app),
         "## AI assistance", __import__("privacy").disclosure(app)["statement"], "",
         "## Enclosed documents"]
    L += [f"{i}. {e}" for i, e in enumerate(enclosed, 1)]
    L += ["", "## Addressing", f"- Jurisdiction overlay: {jur}", f"- Intended recipient: {to_addr}", f"- Basis: {to_note}"]
    if jur == "edmonton":
        L += ["", "<!-- UNCONFIRMED: no Edmonton variance form or submission address was found in the source files. "
              "Recipient is a placeholder; confirm with the plans examiner on the permit file. -->",
              "**Note:** the Edmonton recipient is unconfirmed (no Edmonton form found)."]
    if warnings:
        L += ["", "## Preparer warnings"] + [f"- {w}" for w in warnings]
    L += ["", f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}._", ""]
    return "\n".join(L)


def build_package(app: dict, attachments: list, out_zip: str) -> dict:
    _check_signed(app)
    attachments = list(attachments or [])
    for a in attachments:
        if not os.path.isfile(a):
            raise ValueError(f"Attachment not found: {a}")
    jur = app.get("jurisdiction") or "scc"
    if jur not in RECIPIENTS:
        raise ValueError(f"Unknown jurisdiction overlay '{jur}'")
    to_addr, to_note = RECIPIENTS[jur]
    warnings = []
    if (app.get("declarations") or {}).get("privacy_consent") is not True:
        warnings.append("declarations.privacy_consent is not true; confirm the owner has completed the privacy acknowledgement on the form.")

    with tempfile.TemporaryDirectory() as tmp:
        aid = str(app.get("id") or "application")
        scc = fill_scc(app, os.path.join(tmp, f"SCC_variance_form_{aid}.pdf"))
        warnings += scc["warnings"]
        forms = [scc["path"]]
        if jur == "calgary":
            cal = fill_calgary(app, os.path.join(tmp, f"Calgary_request_for_specific_variance_{aid}.pdf"))
            warnings += ["Calgary: " + w for w in cal["warnings"]]
            forms.append(cal["path"])

        entries, used = [], set()
        for f in forms:
            entries.append((os.path.basename(f), f))
            used.add(os.path.basename(f))
        for a in attachments:
            base, n = os.path.basename(a), 1
            name = base
            while "attachments/" + name in used:
                n += 1
                stem, ext = os.path.splitext(base)
                name = f"{stem}_{n}{ext}"
            used.add("attachments/" + name)
            entries.append(("attachments/" + name, a))
        ev_manifest = ""
        try:  # files attached to Section D items (evidence.py), with a manifest of hashes and check results
            import evidence as _ev
            ev_entries = _ev.package_entries(str(app.get("id") or ""))
            if ev_entries:
                entries += [(arc, p) for arc, p, _r in ev_entries]
                ev_manifest = _ev.manifest_text(ev_entries)
                if any(r["worst"] == "block" for _a, _p, r in ev_entries):
                    warnings.append("Some attached evidence files have blocking readability findings; see evidence/MANIFEST.md.")
        except ImportError:
            pass
        enclosed = [e[0] for e in entries]

        note = _cover_note(app, enclosed + ["submission.eml (draft email)"], jur, to_addr, to_note, warnings)

        msg = EmailMessage()
        msg["To"] = to_addr
        msg["Subject"] = f"Variance request: {(app.get('applicant') or {}).get('owner_name') or 'applicant'} - " \
                         f"{(app.get('location') or {}).get('municipal_address') or 'address not provided'}"
        msg["Date"] = formatdate(localtime=True)
        msg["X-Unsent"] = "1"   # opens as an unsent draft in Outlook; this tool never sends
        msg.set_content(
            "DRAFT - not sent. Review before sending.\n\n"
            "Please find enclosed a variance request and supporting documents.\n\n" + note.split("## Enclosed documents")[0].split("\n", 3)[-1]
            + "\nEnclosed:\n" + "\n".join(f"- {e}" for e in enclosed)
            + "\n\nThis package was prepared with a completeness-checking tool. It is not a determination of safety or equivalence.\n")
        for _, path in entries:
            ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
            main, sub = ctype.split("/", 1)
            with open(path, "rb") as fh:
                msg.add_attachment(fh.read(), maintype=main, subtype=sub, filename=os.path.basename(path))

        os.makedirs(os.path.dirname(os.path.abspath(out_zip)), exist_ok=True)
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for arc, path in entries:
                z.write(path, arc)
            if ev_manifest:
                z.writestr("evidence/MANIFEST.md", ev_manifest)
            z.writestr("cover_note.md", note)
            z.writestr("submission.eml", msg.as_bytes())
    return {"path": os.path.abspath(out_zip), "to": to_addr, "files": enclosed + ["cover_note.md", "submission.eml"],
            "warnings": warnings}
