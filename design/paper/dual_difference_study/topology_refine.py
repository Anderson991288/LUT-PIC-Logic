from topology_screen import *
def deep(task):
    k,mask,old=task
    p=(1,3,2)
    r=np.array([int(x)-1 for x in k])
    m,z=solve(mask,192,p,r,warm=[np.array(old['phases'])],seed=41)
    if m<=old['margin']:
        return k,mask,old
    exact,j,a,b=replay(z,mask,p,r)
    if exact>1e-8:
        assert np.array_equal((a>0)&(b>0),((mask>>BITS)&1).astype(bool))
    return k,mask,dict(margin=exact,phases=z.tolist(),limiting_input=j)
if __name__=="__main__":
    initial=json.loads((HERE/'topology_screen.json').read_text())
    keys=['142324','1421324','3142132','14213241']
    rows={k:{} for k in keys}
    with ProcessPoolExecutor(max_workers=24) as pool:
        for k,m,v in pool.map(deep,[(k,m,initial[k][f'{m:04X}']) for k in keys for m in MASKS]):
            rows[k][f'{m:04X}']=v
    (HERE/'topology_refined.json').write_text(json.dumps(rows,indent=2))
    for k,x in rows.items():
        print(k,min((v['margin'],m) for m,v in x.items()),x['6996']['margin'],x['9669']['margin'])
