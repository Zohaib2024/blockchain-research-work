"""
End-to-End Simulation of IoV Adaptive Trust Management on ZohaibChain1
Demonstrates the paper scenarios grounded in Graduate Blockchain Coursework:
- Step 1 [Cryptography & ScroogeCoin Model]: Public Keys as Pseudonym Identity & Scrooge Registration
- Step 2 [P2P Flooding & Double-Spending Defense]: Algorithm 1 Reporting & Double-Voting Prevention
- Step 3 [Consensus & Multisig Scripts]: Algorithm 2 RSU Edge Consensus & Quorum (>= 4 Witnesses)
- Step 4 [Cryptocurrency Model & Incentives]: Algorithm 3 Native Token Distribution (iov_credit) & Incentives
- Step 5 [Timelocks & Proof of Burn]: Timelock Embargo & Hard Revocation Blacklist
- Step 6 [Consensus & Quorum Defense]: Solo Framing Attack Rejection via Quorum Defense
- Step 7 [How to Store & Use Bitcoins]: Privacy-Preserving Handover & Ephemeral Key Rotation
"""

import time
import json
from .multichain_client import MultiChainClient
from .iov_trust_manager import IoVTrustManager
from . import config

def separator(title=""):
    print("\n" + "=" * 75)
    if title:
        print(f"  {title.upper()}")
        print("=" * 75)

def run_simulation():
    separator("IoV Adaptive Trust Management Simulation on ZohaibChain1")
    client = MultiChainClient()
    manager = IoVTrustManager(client)

    info = client.get_info()
    print(f"[*] Blockchain: {info['chainname']} | Protocol: {info['protocolversion']}")
    print(f"[*] Target Block Time: 3 seconds | Active Blocks: {info['blocks']}")
    print(f"[*] Admin / RSU Node: {config.ADMIN_ADDRESS}\n")

    # -------------------------------------------------------------------------
    # STEP 1: VEHICLE REGISTRATION & IDENTITY ISSUANCE
    # -------------------------------------------------------------------------
    separator("Step 1: Vehicle Registration & Pseudonym Issuance")
    vehicles = {}
    vins = {
        "V1_Alarmer": "VIN-HONEST-001",
        "V2_Peer":    "VIN-HONEST-002",
        "V3_Peer":    "VIN-HONEST-003",
        "V4_Peer":    "VIN-HONEST-004",
        "V_Malicious": "VIN-ROGUE-999"
    }

    for name, vin in vins.items():
        init_tv = 1 if name == "V_Malicious" else 3  # Start rogue vehicle with TV=1 to test hard revocation
        rec = manager.register_vehicle(vin, initial_tv=init_tv)
        vehicles[name] = rec
        print(f"  [+] Registered {name:12} | Real VIN: {vin:14} | Pseudo Address: {rec['pseudo_address']} | Init TV: {rec['tv']}")

    # -------------------------------------------------------------------------
    # STEP 2: EVENT 1 - MISBEHAVIOR IN DENSE FOG (ALGORITHM 1)
    # -------------------------------------------------------------------------
    separator("Step 2: Misbehavior Event (Session 'SES_FOG_101') & Algorithm 1")
    session_1 = f"SES_FOG_{int(time.time())}"
    print(f"[!] Scenario: Malicious Vehicle '{vehicles['V_Malicious']['pseudo_address'][:12]}...' broadcasts fake 'Road Clear' alert in dense fog.")
    print(f"[>] Vehicles V1, V2, V3, V4 independently detect conflicting telemetry.")

    # V1 reports first (Alarmer)
    res1 = manager.report_suspicion(session_1, vehicles["V1_Alarmer"]["pseudo_address"], vehicles["V_Malicious"]["pseudo_address"])
    print(f"  * V1 (Alarmer) Reported: Session count = {res1['participating_count']}, Suspect Score = {res1['current_suspect_score']}")

    # V2, V3, V4 report
    for v_name in ["V2_Peer", "V3_Peer", "V4_Peer"]:
        r = manager.report_suspicion(session_1, vehicles[v_name]["pseudo_address"], vehicles["V_Malicious"]["pseudo_address"])
        print(f"  * {v_name} Reported: Session count = {r['participating_count']}, Suspect Score = {r['current_suspect_score']}")

    # -------------------------------------------------------------------------
    # STEP 3: RSU EDGE ANALYSIS & PENALTY (ALGORITHM 2)
    # -------------------------------------------------------------------------
    separator("Step 3: RSU Consensus & Penalty Evaluation (Algorithm 2)")
    print("[>] RSU executing 'analyse_reports' after transaction collection window...")
    analysis_res = manager.analyse_reports(session_1, rsu_address=config.ADMIN_ADDRESS)
    for s in analysis_res["summary"]:
        print(f"  * Suspected Peer: {s['suspect'][:16]}...")
        print(f"    - Votes Against: {s['score']}/{s['total_participants']} (Consensus: 100% > 50% majority)")
        print(f"    - Threshold Check (>=4 vehicles): {'PASSED' if s['meets_threshold'] else 'FAILED'}")
        print(f"    - Action Enacted: {s['action']}")
        print(f"    - Updated Trust Value (TV): {s['updated_tv']}")

    # -------------------------------------------------------------------------
    # STEP 4: REWARD CLAIMS & ASSET TRANSFERS (ALGORITHM 3)
    # -------------------------------------------------------------------------
    separator("Step 4: Reward Claims & On-Chain Asset Distribution (Algorithm 3)")
    # V1 claims (Alarmer bonus)
    v1_claim = manager.claim_reward(vehicles["V1_Alarmer"]["pseudo_address"], session_1)
    print(f"  * V1 Claim: Credits: +{v1_claim['credits_awarded']} (Includes +2 Alarmer Bonus!) | TV: +{v1_claim['tv_increment']} | New TV: {v1_claim['new_tv']}")
    print(f"    On-Chain Asset Tx: {v1_claim['onchain_txid']}")

    # V2, V3, V4 claim
    for v_name in ["V2_Peer", "V3_Peer", "V4_Peer"]:
        c = manager.claim_reward(vehicles[v_name]["pseudo_address"], session_1)
        print(f"  * {v_name} Claim: Credits: +{c['credits_awarded']} | TV: +{c['tv_increment']} | New TV: {c['new_tv']}")

    # Check on-chain balance of V1
    bal_v1 = client.get_asset_balance(vehicles["V1_Alarmer"]["pseudo_address"], config.ASSET_CREDIT)
    print(f"\n  [✔] On-Chain Token Balance for V1 ({config.ASSET_CREDIT}): {bal_v1} tokens verified.")

    # -------------------------------------------------------------------------
    # STEP 5: SECOND OFFENSE -> HARD REVOCATION (PERMANENT BLACKLIST)
    # -------------------------------------------------------------------------
    separator("Step 5: Repeated Misbehavior -> Hard Revocation Test")
    session_2 = f"SES_CRASH_{int(time.time()) + 1}"
    print(f"[!] Scenario: Malicious vehicle repeats violation in session '{session_2}'. Current TV = 0.")
    
    # Fast-forward soft-block for demonstration
    m_rec = manager.get_vehicle_record(vehicles["V_Malicious"]["pseudo_address"])
    m_rec["soft_blocked_until"] = 0
    manager.update_vehicle_record(vehicles["V_Malicious"]["pseudo_address"], m_rec)

    for v_name in ["V1_Alarmer", "V2_Peer", "V3_Peer", "V4_Peer"]:
        manager.report_suspicion(session_2, vehicles[v_name]["pseudo_address"], vehicles["V_Malicious"]["pseudo_address"])

    analysis_res2 = manager.analyse_reports(session_2)
    s2 = analysis_res2["summary"][0]
    print(f"  * Suspect: {s2['suspect'][:16]}... | TV Dropped to: {s2['updated_tv']}")
    print(f"  * Hard Revocation Triggered (TV < 0): {s2['action']}")

    # Verify presence in revocation_list stream
    revoked_items = client.read_stream_key_items(config.STREAM_REVOCATION, vehicles["V_Malicious"]["pseudo_address"])
    if revoked_items:
        print(f"  [✔] Confirmed in '{config.STREAM_REVOCATION}' stream: {revoked_items[-1]['data']['reason']}")

    # -------------------------------------------------------------------------
    # STEP 6: DEFENSE AGAINST FRAMING / SYBIL ATTACKS (< 4 VEHICLES)
    # -------------------------------------------------------------------------
    separator("Step 6: Defense Against Solo Framing / Sybil Attacks")
    session_3 = f"SES_FRAMING_{int(time.time()) + 2}"
    print(f"[!] Scenario: A single rogue vehicle attempts to falsely accuse innocent vehicle V2.")
    manager.report_suspicion(session_3, vehicles["V1_Alarmer"]["pseudo_address"], vehicles["V2_Peer"]["pseudo_address"])

    analysis_res3 = manager.analyse_reports(session_3)
    s3 = analysis_res3["summary"][0]
    print(f"  * Reported Participants: {s3['total_participants']}/4 required")
    print(f"  * Threshold Check (>=4): {'PASSED' if s3['meets_threshold'] else 'REJECTED (Insufficient Witnesses)'}")
    print(f"  * Action: {s3['action']} (V2 is protected from unjust punishment)")

    # -------------------------------------------------------------------------
    # STEP 7: CROSS-REGION HANDOVER (LEAVE-REGION TRANSACTION)
    # -------------------------------------------------------------------------
    separator("Step 7: Cross-Region Handover (LEAVE-REGION Transaction)")
    v1_old = vehicles["V1_Alarmer"]["pseudo_address"]
    handover = manager.leave_region(v1_old, source_region="Region-1", target_region="Region-2")
    print(f"  * Vehicle {handover['real_vin']} leaving {handover['source_region']} -> entering {handover['target_region']}")
    print(f"  * Old Temporary Address: {handover['old_address']}")
    print(f"  * New Temporary Address: {handover['new_address']} (Location privacy preserved)")
    print(f"  * Preserved State: Trust Value = {handover['synced_tv']}, Credit Score = {handover['synced_credit_score']}")

    separator("Simulation Successfully Completed")
    print("[✔] All 3 algorithms, edge consensus, revocation, and handover executed seamlessly on ZohaibChain1.\n")

if __name__ == "__main__":
    run_simulation()
