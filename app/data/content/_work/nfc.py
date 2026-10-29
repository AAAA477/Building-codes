import pymupdf
d=pymupdf.open("files/codes/NFC_2023AE.pdf")
t="\n".join(f"=====PAGE {i+1}=====\n"+p.get_text() for i,p in enumerate(d))
open("app/data/content/_work/txt/NFC.txt","w",encoding="utf-8").write(t); print(len(d))
