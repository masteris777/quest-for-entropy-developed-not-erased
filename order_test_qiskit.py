"""The order test of #18: does it matter WHEN the late choice is made? A quantum computer answers.

    python order_test_qiskit.py                      # ideal simulator
    python order_test_qiskit.py --noisy              # simulator with a real device's noise (FakeTorino)
    python order_test_qiskit.py --hardware           # least-busy IBM QPU (IBM_QUANTUM_TOKEN in .env)
    python order_test_qiskit.py --replot FILE.json   # redraw from saved counts, no run

Qubits: q0 = P (the photon), q1 = M (the marker). Measuring a qubit is a detector reading it (D1 for P, D2 for M).
Operations: H = the halfway turn (a splitter), P(phi) = the delay, CX = the meeting (P copies its arm into M).

  nomark   H(P) . P(phi) . H(P) . measure P                                   the fringe, no marker
  which    H(P) . CX(P->M) . P(phi) . H(P) . measure P . measure M            M read as it is: flat
  late     H(P) . CX(P->M) . P(phi) . H(P) . measure P  ->  H(M) . measure M  the choice AFTER P landed
  early    H(P) . CX(P->M) . H(M) . measure M  ->  P(phi) . H(P) . measure P  M read BEFORE P even reaches the join

late and early are the same gates in the opposite order. The claim: their sorted curves are identical.
Raw counts are saved to JSON the moment a job returns (hardware time is scarce; never lose a run).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
ROOT = HERE
PHIS_DEG = list(range(0, 361, 30))
SETUPS = ["nomark", "which", "late", "early"]


def circuit(setup: str, phi: float) -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)                                   # c0 = P's detector, c1 = M's detector
    qc.h(0)
    if setup == "nomark":
        qc.p(phi, 0); qc.h(0); qc.measure(0, 0)
        return qc
    qc.cx(0, 1)
    if setup == "which":
        qc.p(phi, 0); qc.h(0); qc.measure(0, 0); qc.measure(1, 1)
    elif setup == "late":
        qc.p(phi, 0); qc.h(0); qc.measure(0, 0); qc.h(1); qc.measure(1, 1)
    elif setup == "early":
        qc.h(1); qc.measure(1, 1); qc.p(phi, 0); qc.h(0); qc.measure(0, 0)
    else:
        raise ValueError(setup)
    return qc


def key(setup: str, phi: float) -> dict:
    """Exact share of P = 0: overall, and within M = 0 / M = 1 (Qiskit's real H: H.P(phi).H lands on 0 with cos^2)."""
    f = np.cos(phi / 2) ** 2
    if setup == "nomark":
        return {"all": f}
    if setup == "which":
        return {"all": 0.5, "g0": 0.5, "g1": 0.5}
    return {"all": 0.5, "g0": f, "g1": 1 - f}


def shares(counts: dict) -> dict:
    tot = sum(counts.values())
    row = {"all": sum(v for k, v in counts.items() if k[-1] == "0") / tot}
    for g in (0, 1):
        sub = {k: v for k, v in counts.items() if len(k) > 1 and k[-2] == str(g)}
        n = sum(sub.values())
        row["g%d" % g] = sum(v for k, v in sub.items() if k[-1] == "0") / n if n else float("nan")
        row["n%d" % g] = n
    return row


def token() -> str:
    t = os.environ.get("IBM_QUANTUM_TOKEN")
    env = os.path.join(ROOT, ".env")
    if not t and os.path.exists(env):
        for line in open(env, encoding="utf-8"):
            if line.startswith("IBM_QUANTUM_TOKEN="):
                t = line.split("=", 1)[1].strip().strip('"')
    if not t:
        sys.exit("no IBM_QUANTUM_TOKEN in the environment or .env")
    return t


def run(mode: str, shots: int, backend_name: str | None) -> dict:
    tags = [(s, d) for s in SETUPS for d in PHIS_DEG]
    circs = [circuit(s, np.radians(d)) for s, d in tags]
    if mode == "hardware":
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
        service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token())
        backend = service.backend(backend_name) if backend_name else service.least_busy(operational=True, simulator=False)
        sampler = SamplerV2(mode=backend)
    else:
        from qiskit_aer import AerSimulator
        from qiskit_aer.primitives import SamplerV2
        if mode == "noisy":
            from qiskit_ibm_runtime.fake_provider import FakeTorino
            backend = AerSimulator.from_backend(FakeTorino())
        else:
            backend = AerSimulator()
        sampler = SamplerV2()
        if mode == "noisy":
            sampler = SamplerV2(options={"backend_options": {"noise_model": backend.options.noise_model}})
    name = getattr(backend, "name", "aer").replace("aer_simulator_from(", "").replace(")", "")
    print(f"backend: {name}  circuits: {len(circs)}  shots each: {shots}  total shots: {len(circs) * shots}")
    pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
    tcs = pm.run(circs)
    t0 = time.time()
    job = sampler.run(tcs, shots=shots)
    job_id = job.job_id() if hasattr(job, "job_id") else None
    if job_id:
        print("job id:", job_id)
    res = job.result()
    counts = [r.data.c.get_counts() for r in res]
    out = {"backend": name, "mode": mode, "shots": shots, "job_id": job_id, "wall_s": round(time.time() - t0, 1),
           "when": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": [{"setup": s, "phi_deg": d, "counts": c} for (s, d), c in zip(tags, counts)]}
    usage = getattr(res, "metadata", {}) or {}
    if usage:
        out["metadata"] = json.loads(json.dumps(usage, default=str))
    os.makedirs(ASSETS, exist_ok=True)
    path = os.path.join(ASSETS, f"qc_order_test_{mode}_{name}.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=1)
    print("saved counts:", path)
    return out


def table(data: dict) -> None:
    by = {}
    for r in data["runs"]:
        by.setdefault(r["setup"], {})[r["phi_deg"]] = shares(r["counts"])
    print(f"\n{'phi':>4} | {'nomark':>6} {'key':>5} | {'late M=0':>8} {'early M=0':>9} {'key':>5} | {'late M=1':>8} {'early M=1':>9} | {'which':>5}")
    worst, zs = 0.0, []
    for d in PHIS_DEG:
        k = key("late", np.radians(d))
        L, E = by["late"][d], by["early"][d]
        for g in ("0", "1"):
            a, b = L["g" + g], E["g" + g]
            p = (a * L["n" + g] + b * E["n" + g]) / (L["n" + g] + E["n" + g])
            se = np.sqrt(max(p * (1 - p), 1e-4) * (1 / L["n" + g] + 1 / E["n" + g]))
            worst = max(worst, abs(a - b)); zs.append((a - b) / se)
        print(f"{d:>4} | {by['nomark'][d]['all']:6.3f} {key('nomark', np.radians(d))['all']:5.3f} | {L['g0']:8.3f} {E['g0']:9.3f} {k['g0']:5.3f} | "
              f"{L['g1']:8.3f} {E['g1']:9.3f} | {by['which'][d]['g0']:5.3f}")
    zs = np.array(zs)
    print(f"\nlate vs early, {len(zs)} sorted points: largest gap {worst:.3f}, largest |z| {abs(zs).max():.2f}, "
          f"chi2 {np.sum(zs ** 2):.1f} on {len(zs)} dof (pure shot noise: chi2 near {len(zs)}, |z| mostly under 2)")


def plot(data: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    by = {}
    for r in data["runs"]:
        by.setdefault(r["setup"], {})[r["phi_deg"]] = shares(r["counts"])
    fine = np.linspace(0, 360, 181)
    BROWN, INK, PUR, GRN = "#8a5a2b", "#23201c", "#6b4fbb", "#12806f"
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.0), sharey=True)
    ax = axes[0]
    ax.plot(fine, [key("nomark", np.radians(x))["all"] for x in fine], "--", color=BROWN, lw=1, alpha=.7)
    ax.plot(PHIS_DEG, [by["nomark"][d]["all"] for d in PHIS_DEG], "o-", color=BROWN, lw=1.6, ms=4, label="no marker")
    ax.set_title("1  the fringe, no marker", fontsize=10)
    ax = axes[1]
    ax.plot(PHIS_DEG, [by["which"][d]["all"] for d in PHIS_DEG], "o-", color=INK, lw=1.6, ms=4, label="all photons")
    ax.plot(PHIS_DEG, [by["which"][d]["g0"] for d in PHIS_DEG], "o-", color=PUR, lw=1, ms=3, alpha=.8, label="M = 0")
    ax.plot(PHIS_DEG, [by["which"][d]["g1"] for d in PHIS_DEG], "o-", color=GRN, lw=1, ms=3, alpha=.8, label="M = 1")
    ax.set_title("2  marker read as it is: no fringe anywhere", fontsize=10)
    ax = axes[2]
    for g, col, lab in (("g0", PUR, "M = 0"), ("g1", GRN, "M = 1")):
        ax.plot(fine, [key("late", np.radians(x))[g] for x in fine], "--", color=col, lw=1, alpha=.6)
        ax.plot(PHIS_DEG, [by["late"][d][g] for d in PHIS_DEG], "o-", color=col, lw=1.6, ms=5, label=f"{lab}, choice after P landed")
        ax.plot(PHIS_DEG, [by["early"][d][g] for d in PHIS_DEG], "s", color=col, ms=9, mfc="none", mew=1.4, label=f"{lab}, M read before P")
    ax.plot(PHIS_DEG, [by["late"][d]["all"] for d in PHIS_DEG], "o-", color=INK, lw=1, ms=3, label="all photons")
    ax.set_title("3  late turn on M, sorted by M: order does not matter", fontsize=10)
    for ax in axes:
        ax.set_xlabel("delay φ (deg)"); ax.set_ylim(-0.03, 1.03); ax.set_xticks([0, 90, 180, 270, 360]); ax.grid(alpha=.25)
        ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)
    axes[0].set_ylabel("share at detector 0 (P = 0)")
    fig.suptitle(f"{data['backend']} ({data['mode']}), {data['shots']} shots per point", fontsize=11)
    fig.tight_layout()
    out = os.path.join(ASSETS, f"qc_order_test_{data['mode']}_{data['backend']}.png")
    fig.savefig(out, dpi=160, facecolor="white")
    print("wrote", out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--noisy", action="store_true")
    g.add_argument("--hardware", action="store_true")
    g.add_argument("--replot")
    ap.add_argument("--backend")
    ap.add_argument("--shots", type=int, default=2000)
    a = ap.parse_args()
    if a.replot:
        data = json.load(open(a.replot, encoding="utf-8"))
    else:
        data = run("hardware" if a.hardware else "noisy" if a.noisy else "ideal", a.shots, a.backend)
    table(data)
    plot(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
