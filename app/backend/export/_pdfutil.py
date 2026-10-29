"""Shared PDF helpers: latin-1 sanitising, wrapping, fit-to-box, flowed supplement pages."""
import pymupdf

FONT = "helv"
_REPL = {"–": "-", "—": "-", "‘": "'", "’": "'", "“": '"', "”": '"',
         "•": "-", "…": "...", " ": " ", "→": "->", "≥": ">=", "≤": "<="}


def clean(s) -> str:
    if s is None:
        return ""
    s = str(s)
    for k, v in _REPL.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


def tlen(s, fs):
    return pymupdf.get_text_length(s, fontname=FONT, fontsize=fs)


def wrap(text, fs, width):
    lines = []
    for para in clean(text).split("\n"):
        cur = ""
        for word in para.split(" "):
            cand = word if not cur else cur + " " + word
            if tlen(cand, fs) <= width:
                cur = cand
                continue
            if cur:
                lines.append(cur)
                cur = ""
            while tlen(word, fs) > width and len(word) > 1:  # hard-break very long tokens
                n = len(word)
                while n > 1 and tlen(word[:n], fs) > width:
                    n -= 1
                lines.append(word[:n])
                word = word[n:]
            cur = word
        lines.append(cur)
    return lines


def fit(text, w, h, max_fs=9.0, min_fs=5.5, multiline=True):
    """Return (fontsize, text_with_newlines, fully_fits). Truncates (with '...') if even min_fs overflows."""
    text = clean(text).strip()
    avail_w, avail_h = max(w - 4, 4), max(h - 2, 4)
    fs = max_fs
    while fs >= min_fs - 1e-6:
        if multiline:
            lines = wrap(text, fs, avail_w)
            if len(lines) * fs * 1.15 <= avail_h:
                return fs, "\n".join(lines), True
        else:
            one = text.replace("\n", " ")
            if tlen(one, fs) <= avail_w and fs * 1.15 <= avail_h:
                return fs, one, True
        fs -= 0.5
    fs = min_fs
    words = text.replace("\n", " ").split(" ")
    lo, hi = 0, len(words)
    while lo < hi:  # longest word prefix that fits with ellipsis
        mid = (lo + hi + 1) // 2
        cand = " ".join(words[:mid]) + "..."
        if multiline:
            ok = len(wrap(cand, fs, avail_w)) * fs * 1.15 <= avail_h
        else:
            ok = tlen(cand, fs) <= avail_w
        if ok:
            lo = mid
        else:
            hi = mid - 1
    cand = (" ".join(words[:lo]) + "...") if lo else "..."
    return fs, ("\n".join(wrap(cand, fs, avail_w)) if multiline else cand), False


def _pdf_str(t):
    return "(" + t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ")"


def set_widget(widget, text, max_fs=9.0, min_fs=5.5):
    """Write text into a text widget with an explicit font size (the form's fields inherit auto-size
    from their parent field, which would ignore our sizing). Returns True if it fit untruncated."""
    r = widget.rect
    multiline = bool(widget.field_flags & 4096)
    fs, val, ok = fit(text, r.width, r.height, max_fs, min_fs, multiline)
    lines = val.split("\n")
    logical = " ".join(lines) if (ok is False) else clean(text).strip()
    widget.text_font = "Helv"
    widget.text_fontsize = fs
    widget.field_value = logical
    widget.update()
    doc = widget.parent.parent
    # explicit DA on the field (and parent) so viewers that regenerate appearances keep our size
    da = f"/Helv {fs:g} Tf 0 g"
    doc.xref_set_key(widget.xref, "DA", _pdf_str(da))
    par = doc.xref_get_key(widget.xref, "Parent")
    if par[0] == "xref":
        doc.xref_set_key(int(par[1].split()[0]), "DA", _pdf_str(da))
    # own appearance stream with our wrapping
    ap = doc.xref_get_key(widget.xref, "AP/N")
    if ap[0] == "xref":
        x = int(ap[1].split()[0])
        lead = fs * 1.15
        if multiline:
            y0 = r.height - 2 - fs * 0.85
        else:
            y0 = (r.height - fs) / 2 + fs * 0.22
        body = ["/Tx BMC", "q", f"1 1 {r.width - 2:.2f} {r.height - 2:.2f} re W n", "BT", "0 g", f"/Helv {fs:g} Tf",
                f"2 {y0:.2f} Td"]
        for i, ln in enumerate(lines):
            if i:
                body.append(f"0 {-lead:.2f} Td")
            body.append(_pdf_str(ln) + " Tj")
        body += ["ET", "Q", "EMC"]
        doc.update_stream(x, "\n".join(body).encode("latin-1"))
    return ok


class Flow:
    """Flow text onto supplementary pages inserted into a doc at a given index."""

    def __init__(self, doc, index, header, width=612, height=792, margin=48):
        self.doc, self.index, self.header = doc, index, header
        self.w, self.h, self.m = width, height, margin
        self.pages = 0
        self.page = None
        self.y = 0
        self._new()

    def _new(self):
        pno = self.index + self.pages
        self.doc.insert_page(pno, width=self.w, height=self.h)
        self.page = self.doc[pno]
        self.pages += 1
        self.page.insert_text((self.m, 30), clean(self.header), fontname="hebo", fontsize=8, color=(0.3, 0.3, 0.3))
        self.y = self.m + 10

    def write(self, text, fs=10, bold=False, indent=0, gap=4):
        font = "hebo" if bold else FONT
        for line in wrap(text, fs, self.w - 2 * self.m - indent):
            if self.y + fs * 1.3 > self.h - self.m:
                self._new()
            self.page.insert_text((self.m + indent, self.y + fs), line, fontname=font, fontsize=fs)
            self.y += fs * 1.3
        self.y += gap
