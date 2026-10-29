import pymupdf,sys,os
out="app/data/content/_work/txt"; os.makedirs(out,exist_ok=True)
for f in ["files/direct/11_Edmonton_Point_Access_Block.pdf","files/direct/10_Edmonton_Emergency_Services_Guideline.pdf","files/direct/09_Calgary_Alt_Solution_Guide.pdf","files/direct/08_CWC_Alt_Solutions_Guide.pdf","files/direct/00_Challenge_Scope.pdf","files/codes/NBC_2023AE_2nd_printing.pdf","files/direct/07_Variance_Form.pdf"]:
    d=pymupdf.open(f); n=os.path.basename(f)[:-4]
    with open(f"{out}/{n}.txt","w",encoding="utf-8") as o:
        for i,p in enumerate(d): o.write(f"\n=====PAGE {i+1}=====\n"+p.get_text())
    print(n,len(d))
