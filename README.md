# Developed, Not Erased

**Article:** [Quest for Entropy #18 — "Developed, Not Erased"](https://questforentropy.com/p/developed-not-erased) · also on [Substack](https://questforentropy.substack.com/p/developed-not-erased)

Companion code for the episode. The article ships with it as `article.md`. The
bench, the whole run one action at a time with every dial, is `bench/index.html`;
the arrow picture of where the fringe goes is `fringe-arrows/index.html`. Open
either in a browser, no server needed.

## Run it

Python 3.10+.

    pip install qiskit qiskit-aer qiskit-ibm-runtime numpy matplotlib
    python order_test_qiskit.py

That runs the order test on an ideal simulator in a few seconds: the fringe with
no marker, the marker read as it is, and the late choice made after the photon
landed and before it reached the join. It prints the table and draws the chart
into `assets/`.

    python order_test_qiskit.py --noisy       # a simulator with a real device's noise
    python order_test_qiskit.py --hardware    # IBM hardware, needs IBM_QUANTUM_TOKEN in the environment or .env

The counts from our hardware run (ibm_marrakesh, 26 September 2026, 2000 shots
per point) are in `assets/qc_order_test_hardware_ibm_marrakesh.json`, exactly as
they came back. To check our numbers without a quantum computer:

    python order_test_qiskit.py --replot assets/qc_order_test_hardware_ibm_marrakesh.json

`python run_all.py` does both, the simulator run and the hardware replot.

## What is in here

| file | what it is |
|---|---|
| `order_test_qiskit.py` | the four circuits, the run, the table and the chart |
| `assets/qc_order_test_hardware_ibm_marrakesh.json` | the raw hardware counts |
| `bench/index.html` | the bench: one photon at a time, every table, every dial |
| `fringe-arrows/index.html` | the arrow picture of the fringe, the marker and the late choice |
| `run_all.py` | the simulator run, then the hardware replot |
| `expected_output/run_all.txt` | what a correct run prints, to diff against |

The simulator draws fresh random shots on every run, so its numbers move within
shot noise; the hardware replot prints the same numbers every time.

## Scope

The circuits are standard delayed-choice circuits, and quantum mechanics
predicts every curve they draw. What the episode adds is a picture: the toy's
tables, step by step. The article's Confession section says exactly where that
line falls.

## Licence

MIT.
