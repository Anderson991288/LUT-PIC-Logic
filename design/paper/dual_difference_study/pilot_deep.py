from simulate import *
from scipy.optimize import check_grad
def run(task):
    mask,window,seed=task
    m,z=solve(mask,128,window,seed=seed)
    return mask,window,m,z
if __name__=='__main__':
    tasks=[(mask,w,i+10) for w in (False,True) for mask in (0x6996,0x9669,0x1689,0xe976) for i in range(6)]
    best={}
    with ProcessPoolExecutor(max_workers=8) as pool:
        for mask,w,m,z in pool.map(run,tasks):
            key=f'{int(w)}_{mask:04x}'
            if key not in best or m>best[key]['margin']:
                _,j,a,b=replay(z,mask,w)
                best[key]=dict(margin=m,phases=z.tolist(),limiting_input=j,d1=a.tolist(),second=b.tolist())
                print(key,m,flush=True)
                (HERE/'pilot.json').write_text(json.dumps(best,indent=2))
