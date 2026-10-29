import re
_T=open("txt/intent2020.txt",encoding="utf-8").read().split("\n")
def get(art,sent):
    key=f"Provision: {art}.({sent})"
    for i,l in enumerate(_T):
        if l.strip()==key:
            out=[];pg=None
            for j in range(i+1,min(i+80,len(_T))):
                s=_T[j].strip()
                if s.startswith("Provision:"): break
                m=re.match(r"=====PAGE (\d+)",s)
                if m: pg=int(m.group(1)); continue
                if s.startswith("©") or s.startswith("Intent Statements") or s=="NBC 2020" or re.fullmatch(r"\d{3,4}",s): continue
                out.append(s)
            txt=" ".join(out)
            ints=re.findall(r"Intent \d+\.\s.*?(?=Intent \d+\.|Objective|$)",txt)
            # intent pdf page: page of the Provision line
            p=None
            for k in range(i,0,-1):
                m=re.match(r"=====PAGE (\d+)",_T[k])
                if m: p=int(m.group(1)); break
            return {"intents":[x.strip() for x in ints],"page":p,"raw":txt}
    return None
if __name__=="__main__":
    import json
    for a,s in [("3.4.2.1",1),("9.8.8.1",4),("9.9.10.1",1),("9.8.8.1",5)]:
        r=get(a,s); print(a,s,json.dumps(r,ensure_ascii=False)[:900])
