import re,sys
_BAD=re.compile(r"(Division|Section|Part|Subsection)\b")
def build(path="app/data/content/_work/txt/NBC_2023AE_2nd_printing.txt"):
    """Map article number -> (pdf_page, title) using body headings (number on its own line, then a Title line,
    then the sentence text starting '1)' or a table/paragraph). Running page headers are rejected."""
    t=open(path,encoding="utf-8").read()
    pages=re.split(r"=====PAGE (\d+)=====",t)
    idx={}
    for k in range(1,len(pages),2):
        pg=int(pages[k]); lines=[l.strip() for l in pages[k+1].split("\n") if l.strip()]
        for i,l in enumerate(lines[:-2]):
            m=re.fullmatch(r"(\d{1,2}\.\d{1,2}\.\d{1,2}\.\d{1,2})\.",l)
            if not m: continue
            nx=lines[i+1]
            if not re.match(r"[A-Z]",nx) or _BAD.match(nx): continue
            # title may wrap to a second line; accept if one of the next 3 lines begins a sentence "1)"
            if any(re.match(r"1\)",x) for x in lines[i+2:i+5]) or "Reserved" in nx:
                idx.setdefault(m.group(1),(pg,nx))
    return idx
if __name__=="__main__":
    idx=build(); print(len(idx))
    for a in sys.argv[1:]: print(a, idx.get(a))
