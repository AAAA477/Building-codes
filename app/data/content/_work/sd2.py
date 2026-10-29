import pymupdf,glob,re
for k in ["bcb-007r1","23-bci-003r1","23-bci-017","bcv-005-2024"]:
    f=[x for x in glob.glob("files/standata/**/*.pdf",recursive=True) if k in x][0]
    d=pymupdf.open(f); print("=====",f)
    for i,p in enumerate(d):
        t=p.get_text()
        if i==0 or re.search(r"3\.4\.2\.1|single exit|one exit|point access",t,re.I): print("--page",i+1); print(re.sub(r"\n+","\n",t)[:2500].encode("ascii","replace").decode())
