"""Retest the most promising fixed port orders with equal restart budgets."""
from port_screen import *

def run(task):
    p,m,old=task
    margin,z=solve(m,192,p,warm=[np.array(old["phases"])],seed=41)
    if margin<=old["margin"]:
        return p,m,old
    exact,j,a,b=replay(z,m,p)
    if exact>1e-8:
        assert np.array_equal((a>0)&(b>0),((m>>BITS)&1).astype(bool))
    return p,m,dict(margin=exact,phases=z.tolist(),limiting_input=j)

if __name__=="__main__":
    rows=json.loads((HERE/"port_screen.json").read_text())
    ranked=sorted(rows,key=lambda k:min(x["margin"] for x in rows[k].values()),reverse=True)
    keys=sorted(set(ranked[:12]+["243"]))
    tasks=[(tuple(int(i)-1 for i in k),int(m,16),v) for k in keys for m,v in rows[k].items()]
    with ProcessPoolExecutor(max_workers=24) as pool:
        for p,m,v in pool.map(run,tasks):
            rows["".join(str(i+1) for i in p)][f"{m:04X}"]=v
    (HERE/"port_screen_refined.json").write_text(json.dumps(rows,indent=2))
    for k in sorted(rows,key=lambda k:min(x["margin"] for x in rows[k].values()),reverse=True):
        print(k,min(x["margin"] for x in rows[k].values()),flush=True)
