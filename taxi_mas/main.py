from __future__ import annotations
import argparse
import json
import os
from dataclasses import asdict

from .sim import TaxiMAS, SimConfig


def parse_args():
    p = argparse.ArgumentParser(description="Taxi Multi-Agent System demo")
    p.add_argument("--steps", type=int, default=800)
    p.add_argument("--n-drivers", type=int, default=35)
    p.add_argument("--request-rate", type=float, default=2.0)
    p.add_argument("--grid", type=int, nargs=2, default=[25, 25], metavar=("W", "H"))
    p.add_argument("--dispatch-every", type=int, default=2)
    p.add_argument("--strategy", type=str, default="auction", choices=["greedy", "auction"])
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--plot", action="store_true")
    p.add_argument("--out", type=str, default="run_output", help="куда сохранить json/графики")
    return p.parse_args()


def main():
    args = parse_args()
    cfg = SimConfig(
        steps=args.steps,
        n_drivers=args.n_drivers,
        request_rate=args.request_rate,
        grid_w=args.grid[0],
        grid_h=args.grid[1],
        dispatch_every=args.dispatch_every,
        strategy=args.strategy,
        seed=args.seed,
    )

    sim = TaxiMAS(cfg)
    summary = sim.run()

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({"config": asdict(cfg), "summary": summary}, f, ensure_ascii=False, indent=2)

    print("\n=== CONFIG ===")
    print(json.dumps(asdict(cfg), ensure_ascii=False, indent=2))
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.plot:
        plot_timeseries(sim, args.out)


def plot_timeseries(sim: TaxiMAS, outdir: str):
    import matplotlib.pyplot as plt

    t = list(range(len(sim.open_requests_ts)))

    plt.figure()
    plt.plot(t, sim.open_requests_ts)
    plt.title("Open requests over time")
    plt.xlabel("tick")
    plt.ylabel("open requests")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "open_requests.png"), dpi=160)

    plt.figure()
    plt.plot(t, sim.completed_ts, label="completed")
    plt.plot(t, sim.canceled_ts, label="canceled")
    plt.title("Completed vs canceled (cumulative)")
    plt.xlabel("tick")
    plt.ylabel("count")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "completed_canceled.png"), dpi=160)

    plt.figure()
    plt.plot(t, sim.avg_wait_ts)
    plt.title("Average wait time (running mean)")
    plt.xlabel("tick")
    plt.ylabel("ticks")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, "avg_wait.png"), dpi=160)

    print(f"\nSaved plots to: {outdir}")


if __name__ == "__main__":
    main()
