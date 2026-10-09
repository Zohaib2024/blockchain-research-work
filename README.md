# Blockchain-Based Adaptive Trust Management in Internet of Vehicles (IoV)

[![MultiChain 2.3.3](https://img.shields.io/badge/MultiChain-2.3.3-blue.svg)](https://www.multichain.com/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Overview

This repository provides a working blockchain-based implementation of the peer-reviewed IEEE research paper:
> **"Blockchain-Based Adaptive Trust Management in Internet of Vehicles Using Smart Contract"**  
> *Pranav Kumar Singh, Roshan Singh, Sunit Kumar Nandi, Kayhan Zrar Ghafoor, Danda B. Rawat, and Sukumar Nandi*  
> **IEEE Transactions on Intelligent Transportation Systems**, DOI: [10.1109/TITS.2020.3004041](https://doi.org/10.1109/TITS.2020.3004041)

The complete implementation translates theoretical mathematical trust models into a functioning, localized private blockchain network on **MultiChain 2.3.3**, implementing Algorithms 1, 2, 3, hard/soft revocation, solo framing defense, and regional handovers.

---

## Architecture & Data Streams Mapping

| Paper Conceptual Entity | MultiChain Implementation Stream / Asset | Functional Responsibility |
| :--- | :--- | :--- |
| **Session Register (`SR`)** | `session_register` | Records active incident sessions, participating witness counts ($s.count$), and primary reporting alarmer address. |
| **Personal Transaction Register (`PTR`)** | `ptr_stream` | Maintains immutable vehicular action logs and reward claims. Guarantees non-repudiation and prevents duplicate voting. |
| **Score Status Register (`SSR`)** | `ssr_stream` | Aggregates suspicion reports against accused vehicles and logs Roadside Unit (RSU) consensus decisions. |
| **Vehicle Register (`VR`)** | `vehicle_register` | Stores dynamic Trust Value ($TV$), wallet balances, penalty timers, and pseudonym credentials. |
| **Revocation List** | `revocation_list` | Holds permanently banned vehicles whose trust score falls below zero ($TV < 0$). |
| **Incentive Tokens** | `iov_credit` | Native cryptocurrency asset minted on the blockchain for rewarding honest reporting vehicles. |

---

## Core Algorithms Implemented

1. **Algorithm 1: Event Suspicion Reporting (`report_suspicion`)**
   - Detects fraudulent or contradictory telemetry warnings.
   - Verifies vehicle registration and transmission eligibility.
   - Enforces single submission per session via `ptr_stream`.

2. **Algorithm 2: RSU Edge Consensus & Trust Update (`analyse_reports`)**
   - **Quorum Assessment**: Requires a minimum of 4 distinct vehicular witnesses ($s.count \ge 4$). Sessions with fewer than 4 witnesses are dismissed without penalty, thwarting solo framing attacks.
   - **Majority Consensus**: Requires more than 50% agreement among witnesses to convict an offender.
   - **Soft Revocation**: Decrements trust score ($TV = TV - 1$) and applies a 60-second communication embargo.
   - **Hard Revocation**: If $TV < 0$, the vehicle address is permanently blacklisted in `revocation_list` and stripped of stream permissions.

3. **Algorithm 3: Reward Claims & Asset Distribution (`claim_reward`)**
   - Verified honest witnesses receive +5 credits and a +1 trust value increment.
   - Primary alarmer vehicle receives an additional +2 credit bonus.
   - Native cryptocurrency tokens (`iov_credit`) are transferred directly to the vehicle address on-chain.

4. **Cross-Region Handover (`leave_region`)**
   - Migrates accumulated trust score and credit balance to the target regional cluster.
   - Issues fresh cryptographic keys and pseudonyms to preserve vehicular location privacy.

---

## Repository Structure

```
.
├── README.md                                          # Documentation & execution guide
├── LICENSE                                            # MIT Open-Source License
├── setup_chain.sh                                     # Automated blockchain setup script
├── contracts/                                         # Solidity smart contracts
│   ├── GlobalTrustManager.sol                         # Central Plane contract
│   └── RegionalTrustManager.sol                       # Regional Edge contract
├── src/                                               # MultiChain trust management engine
│   ├── __init__.py
│   ├── config.py                                      # Chain & RPC configuration
│   ├── multichain_client.py                           # JSON-RPC connector
│   ├── iov_trust_manager.py                           # Algorithms 1-3 & Handover engine
│   ├── simulate_iov.py                                # End-to-end vehicular simulation
│   └── benchmark.py                                   # Performance benchmarking script
└── tests/
    └── test_trust_algorithms.py                       # Automated unit tests
```

---

## Execution Instructions

### Prerequisites
* Linux OS (Ubuntu 20.04/22.04 LTS or compatible)
* MultiChain 2.3+ (`multichaind`, `multichain-cli`, `multichain-util`)
* Python 3.10+

### 1. Initialize the Blockchain
Initialize the private blockchain, launch the background daemon, create the 5 data streams, and issue the native reward asset:
```bash
bash setup_chain.sh
```

Or check status if already running:
```bash
multichain-cli zohaibchain1 getinfo
```

### 2. Run the Full Vehicular Simulation
Executes the complete lifecycle (registration, incident reporting, consensus analysis, soft revocation, hard revocation, solo framing defense, and regional handover):
```bash
python3 -m src.simulate_iov
```

### 3. Run Automated Unit Tests
Verifies duplicate prevention, witness threshold checks ($s.count \ge 4$), and reward distribution:
```bash
python3 -m unittest discover tests
```

### 4. Run Performance Benchmark
Measures transaction throughput (TPS) and execution latency across batch workloads:
```bash
python3 -m src.benchmark
```

---

## License
Licensed under the [MIT License](LICENSE).
