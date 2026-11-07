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
def objective(z, mask, beta, window):
    tape, matrix, derivative = fields(z)
    out = tape[7]
    residual = np.empty(16)
    branch = np.empty(16)
    signs = np.empty(16)
    for j in range(16):
        d = abs(out[j,1])**2 - abs(out[j,3])**2
        e = .3-d if window else abs(out[j,3])**2 - abs(out[j,2])**2
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
        if window:
            a -= b
        else:
            adj[j,3] = b*out[j,3]
            adj[j,2] = -b*out[j,2]
        adj[j,1] = a*out[j,1]
        adj[j,3] -= a*out[j,3]
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

def replay(z, mask, window=False):
    u = np.eye(5, dtype=complex)
    for k,r in enumerate(RAILS):
        u = embed(LOSS*T(*z[2*k:2*k+2]), r, 5) @ u
    p = abs(INPUTS @ u.T)**2
    a = p[:,1]-p[:,3]
    b = .3-a if window else p[:,3]-p[:,2]
    target = ((mask >> BITS)&1).astype(bool)
    m = np.where(target, np.minimum(a,b), np.maximum(-a,-b))
    return float(m.min()), int(np.argmin(m)), a, b

def solve(mask, count, window=False, warm=(), seed=0, goal=np.inf):
    rng = np.random.default_rng(mask+65536*seed)
    best = (-np.inf, None)
    for i in range(len(warm)+count):
        z = warm[i] if i<len(warm) else rng.uniform(-np.pi,np.pi,14)
        for beta in (35., 180.) if count < 32 else (25., 100., 400.):
            z = minimize(objective,z,args=(mask,beta,window),jac=True,method="L-BFGS-B",
                         options={"maxiter":100,"ftol":1e-10}).x
            m = replay(z,mask,window)[0]
            if m > best[0]:
                best = (m,z)
        if best[0] >= goal:
            break
    return best

def pilot():
    z = np.random.default_rng(4).normal(size=14)
    for window in (False,True):
        margin, _, a, b = replay(z, 0x6996, window)
        out = fields(z)[0][-1]
        p = abs(out)**2
        np.testing.assert_allclose(p[:,1]-p[:,3], a, atol=1e-12)
        np.testing.assert_allclose(.3-a if window else p[:,3]-p[:,2], b, atol=1e-12)
        assert abs(objective(z, 0x6996, 1e5, window)[0]+margin) < np.log(32)/1e5
        fn = lambda x: objective(x,0x6996,35.,window)
        for i in range(14):
            v = np.eye(14)[i]*1e-5
            assert abs((fn(z+v)[0]-fn(z-v)[0])/2e-5-fn(z)[1][i]) < 1e-6
        for mask in (0x6996,0x9669,0x1689,0xe976):
            m,zbest = solve(mask,64,window)
            print(window,hex(mask),m,replay(zbest,mask,window)[1],flush=True)

def chunk(task):
    start, end = task
    margins = np.empty(end-start)
    phases = np.empty((end-start,14))
    for i, mask in enumerate(range(start,end)):
        warm = [phases[i-2**k] for k in range(8) if i >= 2**k and (mask >> k)&1]
        m,z = solve(mask,3,warm=warm,goal=.035)
        if m < .035:
            m2,z2 = solve(mask,12,warm=[z],seed=1,goal=.035)
            if m2>m:
                m,z=m2,z2
        margins[i],phases[i]=m,z
    return start,margins,phases

def scan():
    margins = np.full(65536,np.nan)
    phases = np.full((65536,14),np.nan)
    with ProcessPoolExecutor(max_workers=24) as pool:
        for start,m,z in pool.map(chunk,[(i,i+256) for i in range(0,65536,256)]):
            margins[start:start+len(m)],phases[start:start+len(m)] = m,z
            print(start+len(m),int(np.sum(margins>1e-8)),flush=True)
            if start%2048 == 0:
                np.savez(HERE/"scan_checkpoint.npz", margins=margins,phases=phases)
    np.savez(HERE/"scan.npz",margins=margins,phases=phases)

if __name__ == "__main__":
    if sys.argv[1] == "pilot":
        pilot()
    else:
        scan()


