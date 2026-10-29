import pymupdf,glob,re
for f in sorted(glob.glob("files/standata/**/*.pdf",recursive=True)):
    try: d=pymupdf.open(f)
    except Exception as e: continue
    t=" ".join(p.get_text() for p in d)
    n=len(re.findall(r"\b(exits?|stair|stairs|stairway|egress|3\.4\.2\.1)\b",t,re.I))
    s=len(re.findall(r"3\.4\.2\.1|single exit|one exit|point access",t,re.I))
    if n>=4 or s: print(n,s,len(d),f[-70:])
