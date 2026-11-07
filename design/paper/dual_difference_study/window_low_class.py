"""Re-evaluate the original window on the reported low-margin NPN orbit."""
from itertools import permutations
from simulate import *

def run(mask):
    m,z=solve(mask,32,window=True,seed=20,goal=.08)
    return mask,m,z

if __name__=="__main__":
    masks=set()
    for order in permutations(range(4)):
        permuted=(((BITS[:,None]>>order)&1)*(1<<np.arange(4))).sum(axis=1)
        for flip in range(16):
            for original in (0x1689,0xe976):
                masks.add(int(np.sum(((original>>(permuted^flip))&1)<<BITS)))
    with ProcessPoolExecutor(max_workers=10) as pool:
        rows=list(pool.map(run,sorted(masks),chunksize=4))
    rows.sort(key=lambda row:row[1])
    payload=[dict(mask=mask,margin=m,phases=z.tolist()) for mask,m,z in rows]
    (HERE/"window_low_class.json").write_text(json.dumps(payload,indent=2))
    print(len(rows),[(hex(mask),m) for mask,m,_ in rows[:10]])
