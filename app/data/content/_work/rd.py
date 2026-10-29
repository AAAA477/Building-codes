import pymupdf,sys,glob,re
f=glob.glob("files/standata/**/*"+sys.argv[1]+"*.pdf",recursive=True)[0]
d=pymupdf.open(f)
o="".join(f"\n=====PAGE {i+1}=====\n"+re.sub(r"\n+","\n",p.get_text()) for i,p in enumerate(d))
open(sys.argv[2],"w",encoding="utf-8").write(o)
