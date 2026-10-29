import pymupdf,glob,re,json,os,sys
rows=[]
for f in sorted(glob.glob("files/standata/**/*.pdf",recursive=True)):
    d=pymupdf.open(f); t=d[0].get_text()
    full="\n".join(p.get_text() for p in d)
    lines=[l.strip() for l in t.split("\n") if l.strip()]
    m=re.search(r"STANDATA\s+(variance|interpretation|bulletin)\s+([0-9A-Z\-/R]+)",t,re.I)
    print(os.path.basename(f)[:70],"|",m.group(0) if m else None,"|"," / ".join(lines[3:9])[:160].encode("ascii","replace").decode())
