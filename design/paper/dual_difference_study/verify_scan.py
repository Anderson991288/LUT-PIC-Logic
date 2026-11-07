"""Replay the exhaustive scan and deepen searches on low-margin masks."""
from simulate import *

def deepen(task):
    mask, phase, margin = task
    m,z = solve(mask,64,warm=[phase],seed=3,goal=.075)
    return (mask,m,z) if m>margin else (mask,margin,phase)

def summarize(margins):
    positive = margins > 1e-8
    return dict(total=len(margins), positive=int(positive.sum()),
                worst=float(margins.min()), worst_mask=f"0x{margins.argmin():04X}",
                worst_positive=float(margins[positive].min()) if positive.any() else None,
                median=float(np.median(margins)),
                at_least={str(t):int((margins>=t).sum()) for t in (.03,.035,.05,.075,.1,.15)},
                lowest=[dict(mask=f"0x{i:04X}",margin=float(margins[i])) for i in np.argsort(margins)[:30]])

if __name__ == "__main__":
    data=np.load(HERE/"scan.npz")
    margins,phases=data["margins"],data["phases"]
    assert np.isfinite(margins).all() and len(margins)==65536
    baseline=summarize(margins)
    pilot=json.loads((HERE/"pilot.json").read_text())
    for key, witness in pilot.items():
        if key.startswith("0_"):
            i=int(key[2:],16)
            if witness["margin"]>margins[i]:
                margins[i],phases[i]=witness["margin"],witness["phases"]
    print(json.dumps(baseline),flush=True)
    low=np.flatnonzero(margins<.05)
    with ProcessPoolExecutor(max_workers=20) as pool:
        tasks=((int(i),phases[i],margins[i]) for i in low)
        for mask,m,z in pool.map(deepen,tasks,chunksize=4):
            margins[mask],phases[mask]=m,z
    for i,z in enumerate(phases):
        m,_,a,b=replay(z,i)
        assert abs(m-margins[i])<1e-10
        if m>1e-8:
            assert np.array_equal((a>0)&(b>0),((i>>BITS)&1).astype(bool))
    np.savez_compressed(HERE/"verified_scan.npz",margins=margins,phases=phases)
    summary=dict(initial=baseline,refined_masks=len(low),verified=summarize(margins))
    (HERE/"summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary["verified"]),flush=True)

