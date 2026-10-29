import pymupdf,sys
d=pymupdf.open("files/codes/NBC_2023AE_2nd_printing.pdf")
p=d[int(sys.argv[1])-1]
ws=p.get_text("words")
rows={}
for w in ws: rows.setdefault(round(w[1]/3),[]).append(w)
for k in sorted(rows):
    r=sorted(rows[k]); print(round(r[0][1]), " | ".join(f"{round(x[0])}:{x[4]}" for x in r))
