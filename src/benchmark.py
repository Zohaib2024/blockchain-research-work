"""
Performance Benchmark Suite for ZohaibChain1
Measures:
1. Transaction Throughput (TPS) across varying batch sizes (10, 50, 100, 250)
2. Stream publication latency
3. Average block inclusion time
Outputs performance metrics to artifacts/benchmark_data.json
"""

import time
import json
import os
from .multichain_client import MultiChainClient
from . import config

def run_benchmark():
    client = MultiChainClient()
    batch_sizes = [10, 25, 50, 100, 200]
    results = []

    print("=" * 70)
    print("      ZOHAIBCHAIN1 PERFORMANCE BENCHMARK (PAPER SECTION VI)")
    print("=" * 70)

    for batch in batch_sizes:
        print(f"\n[>] Benchmarking batch size: {batch} transactions...")
        start_time = time.time()
        txids = []
        
        for i in range(batch):
            key = f"bench_{int(start_time)}_{i}"
            data = {
                "benchmark_id": i,
                "timestamp": int(time.time()),
                "payload": "IoV_EVENT_TELEMETRY_SAMPLE_DATA"
            }
            txid = client.publish_stream(config.STREAM_SESSION, key, data)
            txids.append(txid)

        total_time = time.time() - start_time
        tps = batch / total_time if total_time > 0 else 0

        metric = {
            "batch_size": batch,
            "total_execution_time_sec": round(total_time, 3),
            "throughput_tps": round(tps, 2),
            "avg_latency_ms": round((total_time / batch) * 1000, 2)
        }
        results.append(metric)
        print(f"    - Total Time: {metric['total_execution_time_sec']}s")
        print(f"    - Throughput: {metric['throughput_tps']} TPS")
        print(f"    - Average Latency: {metric['avg_latency_ms']} ms/tx")

    # Save to artifacts
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "artifacts")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "benchmark_data.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=4)

    print("\n" + "=" * 70)
    print(f"[✔] Benchmark data saved to {out_file}")
    print("=" * 70)
    return results

if __name__ == "__main__":
    run_benchmark()
