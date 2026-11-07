"""Static B7 LUT4 synthesis and exact replay for dual zero-threshold AND."""
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import sys
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from numba import njit
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from common.mzi import B7_OPS, R_AMP, T, embed

RAILS = np.array([r for r, _ in B7_OPS])
LOSS = 10 ** (-0.9 / 20)
BITS = np.arange(16)
INPUTS = np.column_stack(((BITS[:, None] >> np.arange(4)) & 1, np.full(16, R_AMP))).astype(np.complex128)

@njit(cache=True)
def fields(z):
    tape = np.empty((8, 16, 5), np.complex128)
    matrix = np.empty((7, 2, 2), np.complex128)
    derivative = np.empty_like(matrix)
    tape[0] = INPUTS
    for k, r in enumerate(RAILS):
        p = np.exp(1j*z[2*k])
        q = np.exp(1j*z[2*k+1])
        a = LOSS*(p-1)/2
        b = LOSS*1j*(p+1)/2
        matrix[k, 0, 0] = a*q
        matrix[k, 0, 1] = b
        matrix[k, 1, 0] = b*q
        matrix[k, 1, 1] = -a
        da = LOSS*1j*p/2
        derivative[k, 0, 0] = da*q
        derivative[k, 0, 1] = 1j*da
        derivative[k, 1, 0] = 1j*da*q
        derivative[k, 1, 1] = -da
        tape[k+1] = tape[k]
        for j in range(16):
            for i in range(2):
                tape[k+1,j,r+i] = (matrix[k,i,0]*tape[k,j,r]
                                      + matrix[k,i,1]*tape[k,j,r+1])
    return tape, matrix, derivative

@njit(cache=True)
def objective(z, mask, beta, ports):
    tape, matrix, derivative = fields(z)
    out = tape[7]
    hi, mid, lo = ports
    residual = np.empty(16)
    branch = np.empty(16)
    signs = np.empty(16)
    for j in range(16):
        d = abs(out[j,hi])**2 - abs(out[j,mid])**2
        e = abs(out[j,mid])**2 - abs(out[j,lo])**2
        s = 1 if (mask >> j)&1 else -1
        signs[j] = s
        a, b = -beta*d, -beta*e
        pivot = max(a,b)
        ea, eb = np.exp(a-pivot), np.exp(b-pivot)
        residual[j] = s*(pivot+np.log(ea+eb))/beta
        branch[j] = ea/(ea+eb)
    pivot = np.max(residual)
    weights = np.exp(beta*(residual-pivot))
    total = weights.sum()
    adj = np.zeros((16,5), np.complex128)
    for j in range(16):
        w = -2*signs[j]*weights[j]/total
        a, b = w*branch[j], w*(1-branch[j])
        adj[j,mid] = b*out[j,mid]
        adj[j,lo] = -b*out[j,lo]
        adj[j,hi] = a*out[j,hi]
        adj[j,mid] -= a*out[j,mid]
    grad = np.zeros(14)
    for k in range(6,-1,-1):
        r = RAILS[k]
        for j in range(16):
            x,y = tape[k,j,r],tape[k,j,r+1]
            u,v = adj[j,r],adj[j,r+1]
            grad[2*k] += (u.conjugate()*(derivative[k,0,0]*x+derivative[k,0,1]*y)
                         +v.conjugate()*(derivative[k,1,0]*x+derivative[k,1,1]*y)).real
            grad[2*k+1] += (1j*x*(u.conjugate()*matrix[k,0,0]+v.conjugate()*matrix[k,1,0])).real
            adj[j,r] = matrix[k,0,0].conjugate()*u+matrix[k,1,0].conjugate()*v
            adj[j,r+1] = matrix[k,0,1].conjugate()*u+matrix[k,1,1].conjugate()*v
    return pivot+np.log(total)/beta, grad

def replay(z, mask, ports):
    u = np.eye(5, dtype=complex)
    for k,r in enumerate(RAILS):
        u = embed(LOSS*T(*z[2*k:2*k+2]), r, 5) @ u
    p = abs(INPUTS @ u.T)**2
    hi, mid, lo = ports
    a = p[:,hi]-p[:,mid]
    b = p[:,mid]-p[:,lo]
    target = ((mask >> BITS)&1).astype(bool)
    m = np.where(target, np.minimum(a,b), np.maximum(-a,-b))
    return float(m.min()), int(np.argmin(m)), a, b

def solve(mask, count, ports, warm=(), seed=0):
    rng = np.random.default_rng(mask+65536*seed)
    best = (-np.inf, None)
    for i in range(len(warm)+count):
        z = warm[i] if i<len(warm) else rng.uniform(-np.pi,np.pi,14)
        for beta in (35., 180.) if count < 32 else (25., 100., 400.):
            z = minimize(objective,z,args=(mask,beta,ports),jac=True,method="L-BFGS-B",
                         options={"maxiter":100,"ftol":1e-10}).x
            m = replay(z,mask,ports)[0]
            if m > best[0]:
                best = (m,z)
    return best


from itertools import permutations

MASKS = (0x6996,0x9669,0x1689,0xE976,0xE93E,0x79E6,0x48C7,0x8669)
PORTS = tuple(permutations(range(5),3))
BASE = (1,3,2)

def evaluate(task):
    ports,mask,count=task
    m,z=solve(mask,count,ports)
    exact,j,a,b=replay(z,mask,ports)
    assert abs(exact-m)<1e-12
    if m>1e-8:
        assert np.array_equal((a>0)&(b>0),((mask>>BITS)&1).astype(bool))
    return ports,mask,dict(margin=m,phases=z.tolist(),limiting_input=j)

if __name__=="__main__":
    rng=np.random.default_rng(19)
    z=rng.normal(size=14)
    for ports in PORTS:
        m,*_=replay(z,0x6996,ports)
        assert abs(objective(z,0x6996,1e5,ports)[0]+m)<np.log(32)/1e5
        f,g=objective(z,0x6996,35.,ports)
        for v,analytic in zip(np.eye(14)*1e-5,g):
            fd=(objective(z+v,0x6996,35.,ports)[0]-objective(z-v,0x6996,35.,ports)[0])/2e-5
            assert abs(fd-analytic)<1e-6
    rows={}
    with ProcessPoolExecutor(max_workers=24) as pool:
        for ports,mask,result in pool.map(evaluate,[(p,m,32) for p in PORTS for m in MASKS]):
            key=''.join(str(i+1) for i in ports)
            rows.setdefault(key,{})[f'{mask:04X}']=result
            if len(rows[key])==len(MASKS):
                print(key,min(v['margin'] for v in rows[key].values()),flush=True)
    (HERE/'port_screen.json').write_text(json.dumps(rows,indent=2))
