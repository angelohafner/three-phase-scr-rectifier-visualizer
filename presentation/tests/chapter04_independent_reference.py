"""Independent six-pulse LCC/CCC reference using SciPy event integration.

This test DOES NOT import or reuse the JavaScript solver equations, shooting
code, or RK4 implementation. It independently integrates phase capacitor
states and incoming-valve current until the actual transfer event.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import root

ROOT=Path(__file__).resolve().parents[2]
PAIRS=((0,2),(1,2),(1,0),(2,0),(2,1),(0,1))


def reference(params, samples=1800):
    a=float(params["alpha"])*math.pi/180
    current=float(params["idc"])
    peak=float(params["vPeak"])
    L=float(params["LmH"])/1000
    resistance=float(params["R"])
    frequency=float(params["f"])
    capacitance=float(params["CmF"])/1000
    XL=2*math.pi*frequency*L
    XC=1/(2*math.pi*frequency*capacitance) if capacitance else 0

    def source(t):
        return peak*np.cos(t+a-np.arange(3)*2*math.pi/3)

    def sector(k, vc):
        old=PAIRS[(k-1)%6]
        new=PAIRS[k]
        upper=old[0]!=new[0]
        outgoing=old[0] if upper else old[1]
        incoming=new[0] if upper else new[1]
        stationary=old[1] if upper else old[0]
        sign=1 if upper else -1
        start,stop=k*math.pi/3,(k+1)*math.pi/3

        def ode(t,x):
            i=np.zeros(3)
            i[incoming]=x[3]
            i[outgoing]=sign*current-x[3]
            i[stationary]=-sign*current
            dv=XC*i
            di=((source(t)[incoming]-source(t)[outgoing])
                -(x[incoming]-x[outgoing])
                -resistance*(i[incoming]-i[outgoing]))/(2*XL)
            return np.r_[dv,di]

        def complete(t,x):
            return sign*x[3]-current
        complete.terminal=True
        complete.direction=1
        initial=np.r_[vc,0.]
        if ode(start,initial)[3]*sign <= 0:
            raise RuntimeError("Invalid forward commutation at firing")
        sol=solve_ivp(ode,(start,stop),initial,events=complete,
                      atol=1e-12,rtol=3e-10,max_step=.002,dense_output=True)
        if len(sol.t_events[0])!=1:
            raise RuntimeError("Commutation did not complete")
        event=sol.t_events[0][0]
        conducting=np.zeros(3)
        conducting[new[0]]=current
        conducting[new[1]]=-current
        end=sol.y_events[0][0][:3]+XC*conducting*(stop-event)
        return end,(start,event,stop,sol,old,new,sign,outgoing,incoming,stationary,conducting)

    def cycle(initial,keep=False):
        vc=np.array([initial[0],initial[1],-initial[0]-initial[1]])
        timeline=[]
        for k in range(6):
            vc,entry=sector(k,vc)
            timeline.append(entry)
        if not keep:
            return vc[:2]-initial
        times=np.linspace(0,2*math.pi,samples,endpoint=False)
        phase_samples=np.empty((samples,3))
        current_samples=np.empty((samples,3))
        capacitor_samples=np.empty((samples,3))
        mu=[]
        for k,(begin,end,stop,sol,old,new,sign,outgoing,incoming,stationary,conducting) in enumerate(timeline):
            mu.append((end-begin)*180/math.pi)
            for idx in np.where((times>=begin-1e-12)&(times<stop-1e-12))[0]:
                t=times[idx]
                if t<end:
                    state=sol.sol(t)
                    capacitor=state[:3]
                    i=np.zeros(3)
                    i[incoming]=state[3]
                    i[outgoing]=sign*current-state[3]
                    i[stationary]=-sign*current
                else:
                    state=sol.sol(end)
                    capacitor=state[:3]+XC*conducting*(t-end)
                    i=conducting
                phase_samples[idx]=source(t)
                current_samples[idx]=i
                capacitor_samples[idx]=capacitor
        harmonics=np.exp(-1j*times)
        V1=2*np.mean(phase_samples*harmonics[:,None],axis=0)
        I1=2*np.mean(current_samples*harmonics[:,None],axis=0)
        complex_power=np.sum(V1*np.conj(I1))/2/1.5
        drive=source(0)[2]-source(0)[1]-(capacitor_samples[0,2]-capacitor_samples[0,1])
        drive-=resistance*(current_samples[0,2]-current_samples[0,1])
        return {"mu":float(np.mean(mu)),"Q":float(complex_power.imag),
                "P":float(complex_power.real),"signed_drive":float(-drive),
                "vc_peak":float(np.max(np.abs(capacitor_samples)))}

    if XC:
        # Build an initial capacitor-voltage estimate independently from
        # the integrated LCC current waveform (not from the CCC JS solver).
        ref=reference({**params,"CmF":0},samples=720)
        guess=np.array([-.01,-.075])*(26/float(params["CmF"]))*(current/.8)
        result=root(lambda x:cycle(x),guess,tol=1e-9)
        if np.max(np.abs(cycle(result.x)))>1e-7:
            raise RuntimeError("Independent periodic root failed")
        initial=result.x
    else:
        initial=np.array([0.,0.])
    return cycle(initial,keep=True)


def javascript_result(params):
    program=(
        "const model=require('./presentation/src/ccc_model.js');"
        "const result=model.solve(JSON.parse(process.argv[1]));"
        "if(!result.valid)throw Error(result.error);"
        "const t=result.traces[0],p=result.params;"
        "const drive=-((t.source[2]-t.source[1])"
        "-(t.capacitors[2]-t.capacitors[1])"
        "-p.R*(t.current[2]-t.current[1]));"
        "console.log(JSON.stringify({mu:result.avgMu,Q:result.powers.Q,"
        "P:result.powers.P,signed_drive:drive}));"
    )
    completed=subprocess.run(["node","-e",program,json.dumps(params)],
                             cwd=ROOT,check=True,capture_output=True,text=True)
    return json.loads(completed.stdout)


conditions={"alpha":15,"idc":.8,"vPeak":1,"LmH":.24,
            "R":.012,"f":60,"qShunt":0}
records=[]
for size in (0,12,26,80):
    parameters={**conditions,"CmF":size}
    ref=reference(parameters)
    js=javascript_result(parameters)
    assert abs(ref["mu"]-js["mu"])<.018,(size,ref,js)
    assert abs(ref["Q"]-js["Q"])<.00025,(size,ref,js)
    assert abs(ref["P"]-js["P"])<.00025,(size,ref,js)
    assert abs(ref["signed_drive"]-js["signed_drive"])<.0003
    records.append({"CmF":size,"independent":ref,"javascript":js})

plain=records[0]["independent"]
ccc=records[2]["independent"]
assert ccc["mu"]<plain["mu"],"Series C must shorten nominal overlap"
assert ccc["Q"]<plain["Q"],"Series C must reduce nominal fundamental Q"
assert ccc["signed_drive"]>plain["signed_drive"],"Series C must assist initial commutation"
assert ccc["vc_peak"]>.05,"Capacitor voltage must evolve dynamically"

# Verify a second matched physical operating point, not only a fitted baseline.
for size in (0,26):
    parameters={**conditions,"alpha":30,"idc":1,"LmH":.32,"CmF":size}
    ref=reference(parameters,samples=1200)
    js=javascript_result(parameters)
    assert abs(ref["mu"]-js["mu"])<.02,(size,ref,js)
    assert abs(ref["Q"]-js["Q"])<.00035,(size,ref,js)

print("PASS: independent SciPy event solver matches JS μ/P/Q and commutating drive in six scenarios.")
print(json.dumps(records,indent=2))
