"""Everything this companion claims, in one command: the order test on the ideal
simulator, then the saved hardware counts replotted.

    python run_all.py
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    print("=" * 72)
    print("THE ORDER TEST, IDEAL SIMULATOR")
    print("=" * 72, flush=True)
    subprocess.run([sys.executable, str(HERE / "order_test_qiskit.py")], check=True, cwd=HERE)
    print()
    print("=" * 72)
    print("THE HARDWARE COUNTS, REPLOTTED (ibm_marrakesh)")
    print("=" * 72, flush=True)
    subprocess.run([sys.executable, str(HERE / "order_test_qiskit.py"), "--replot",
                    str(HERE / "assets" / "qc_order_test_hardware_ibm_marrakesh.json")], check=True, cwd=HERE)


if __name__ == "__main__":
    main()
