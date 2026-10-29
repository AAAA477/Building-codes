import pymupdf,re
d=pymupdf.open("files/codes/NBC_2020_Intent_Supplement.pdf"); print(len(d))
out=open("app/data/content/_work/txt/intent2020.txt","w",encoding="utf-8")
for i,p in enumerate(d): out.write(f"\n=====PAGE {i+1}=====\n"+p.get_text())
