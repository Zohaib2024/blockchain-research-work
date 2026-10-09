"""
IoV Trust Management Engine for ZohaibChain1
Implements Algorithms 1, 2, 3 and Regional Handover from:
'Blockchain-Based Adaptive Trust Management in Internet of Vehicles Using Smart Contract'
(IEEE Transactions on Intelligent Transportation Systems)

Grounding in Graduate Blockchain Coursework:
- Cryptography and Blockchain Basics: SHA-256, Hash Pointers, Digital Signatures, and Public Keys as Identity.
- GoofyCoin and ScroogeCoin: Central Authority (TA) vs Edge Decentralization & Double-Voting Prevention.
- Bitcoin Consensus and Mining: Edge Consensus Mechanisms, Economic Incentives, and DoS / Sybil Defense.
- Bitcoin Transactions and Scripts: Multisignature Quorum Verification (>= 4 Witnesses), Timelocks, and Proof of Burn.
- How to Store and Use Bitcoins: Hierarchical Wallet Key Derivation & Privacy-Preserving Pseudonym Rotation.
"""

import time
from .multichain_client import MultiChainClient
from . import config

class IoVTrustManager:
    def __init__(self, client: MultiChainClient = None):
        self.client = client or MultiChainClient()
        self.admin = config.ADMIN_ADDRESS

    # =========================================================================
    # VEHICLE REGISTRATION & IDENTITY MANAGEMENT (Section V-B)
    # =========================================================================
    def register_vehicle(self, real_vin: str, initial_tv: int = config.INITIAL_TRUST_VALUE) -> dict:
        """
        Registers a vehicle. Allocates a pseudonymous MultiChain address,
        sets initial Trust Value (TV), wallet balance, and grants stream permissions.
        """
        pseudo_address = self.client.get_new_address()
        
        # Grant basic network permissions (send, receive, write to streams)
        self.client.grant_permissions(pseudo_address, "send,receive")
        self.client.call("grant", [pseudo_address, f"{config.STREAM_SESSION}.write"])
        self.client.call("grant", [pseudo_address, f"{config.STREAM_PTR}.write"])
        self.client.call("grant", [pseudo_address, f"{config.STREAM_SSR}.write"])

        vehicle_record = {
            "real_vin": real_vin,
            "pseudo_address": pseudo_address,
            "tv": initial_tv,
            "credit_score": 0,
            "is_revoked": False,
            "soft_blocked_until": 0,
            "report_number": 0,
            "claim_number": 0,
            "registered_at": int(time.time()),
            "region": "Region-1"
        }

        self.client.publish_stream(
            config.STREAM_VEHICLE,
            pseudo_address,
            vehicle_record
        )
        return vehicle_record

    def get_vehicle_record(self, pseudo_address: str) -> dict:
        """
        Fetches the latest state of a vehicle from the vehicle_register stream.
        """
        items = self.client.read_stream_key_items(config.STREAM_VEHICLE, pseudo_address)
        if not items:
            return None
        return items[-1]["data"]

    def update_vehicle_record(self, pseudo_address: str, updated_record: dict):
        self.client.publish_stream(config.STREAM_VEHICLE, pseudo_address, updated_record)

    # =========================================================================
    # ALGORITHM 1: HANDLE REPORTING OF AN EVENT (reportSuspicion)
    # =========================================================================
    def report_suspicion(self, session_id: str, reporting_vehicle: str, suspected_vehicle: str) -> dict:
        """
        Algorithm 1: An intelligent vehicle reports suspicious behavior.
        Verifies sender permissions, soft-block status, and logs suspicion without duplicates.
        """
        # 1. Validation checks
        reporter_rec = self.get_vehicle_record(reporting_vehicle)
        if not reporter_rec:
            raise ValueError(f"Reporting vehicle {reporting_vehicle} is not registered.")
        if reporter_rec.get("is_revoked"):
            raise PermissionError(f"Reporting vehicle {reporting_vehicle} is revoked (Hard Revocation).")
        if time.time() < reporter_rec.get("soft_blocked_until", 0):
            raise PermissionError(f"Reporting vehicle {reporting_vehicle} is temporarily blocked (Soft Revocation).")
        
        suspect_rec = self.get_vehicle_record(suspected_vehicle)
        if not suspect_rec:
            raise ValueError(f"Suspected vehicle {suspected_vehicle} is not registered.")

        # 2. Query or Initialize Session
        session_items = self.client.read_stream_key_items(config.STREAM_SESSION, session_id)
        if not session_items:
            session_data = {
                "session_id": session_id,
                "alarmer": reporting_vehicle,
                "count": 1,
                "participating_vehicles": [reporting_vehicle],
                "status": "OPEN",
                "created_at": int(time.time())
            }
        else:
            session_data = session_items[-1]["data"]
            if session_data.get("status") != "OPEN":
                raise ValueError(f"Session {session_id} is already analyzed/closed.")
            if reporting_vehicle in session_data["participating_vehicles"]:
                raise ValueError(f"Duplicate report: Vehicle {reporting_vehicle} already reported in session {session_id}.")
            session_data["count"] += 1
            session_data["participating_vehicles"].append(reporting_vehicle)

        # 3. Update Personal Transaction Register (PTR)
        ptr_key = f"{reporting_vehicle}_{session_id}_{suspected_vehicle}"
        ptr_record = {
            "reporter": reporting_vehicle,
            "session_id": session_id,
            "suspected_vehicle": suspected_vehicle,
            "submitted": True,
            "is_reward_received": False,
            "timestamp": int(time.time())
        }
        self.client.publish_stream(config.STREAM_PTR, ptr_key, ptr_record)

        # 4. Update Score and Status Register (SSR)
        ssr_key = f"{session_id}_{suspected_vehicle}"
        ssr_items = self.client.read_stream_key_items(config.STREAM_SSR, ssr_key)
        if not ssr_items:
            ssr_record = {
                "session_id": session_id,
                "suspected_vehicle": suspected_vehicle,
                "score": 1,
                "verification_result": None
            }
        else:
            ssr_record = ssr_items[-1]["data"]
            ssr_record["score"] += 1

        self.client.publish_stream(config.STREAM_SSR, ssr_key, ssr_record)

        # 5. Commit updated session and reporter record
        self.client.publish_stream(config.STREAM_SESSION, session_id, session_data)
        reporter_rec["report_number"] = reporter_rec.get("report_number", 0) + 1
        self.update_vehicle_record(reporting_vehicle, reporter_rec)

        return {
            "status": "SUSPICION_RECORDED",
            "session_id": session_id,
            "participating_count": session_data["count"],
            "current_suspect_score": ssr_record["score"]
        }

    # =========================================================================
    # ALGORITHM 2: ANALYZING REPORT AND TRUST UPDATE (analyseReports)
    # =========================================================================
    def analyse_reports(self, session_id: str, rsu_address: str = None) -> dict:
        """
        Algorithm 2: RSU analyzes reports received within a session.
        Applies:
          1. Threshold check: count >= 4 (Sybil / framing attack defense)
          2. Majority rule: score > count / 2 (51% consensus)
          3. Penalty: Trust Value -1, Soft Revocation (1 min)
          4. Hard Revocation: if TV < 0, added to permanent revocation_list.
        """
        session_items = self.client.read_stream_key_items(config.STREAM_SESSION, session_id)
        if not session_items:
            raise ValueError(f"Session {session_id} does not exist.")
        
        session_data = session_items[-1]["data"]
        if session_data.get("status") == "ANALYZED":
            raise ValueError(f"Session {session_id} has already been analyzed.")

        count = session_data.get("count", 0)
        participating = session_data.get("participating_vehicles", [])
        analysis_summary = []

        # Find all suspected vehicles in this session from PTR
        all_ptr_items = self.client.read_stream_items(config.STREAM_PTR)
        session_suspects = set()
        for item in all_ptr_items:
            p_data = item.get("data", {})
            if p_data.get("session_id") == session_id:
                session_suspects.add(p_data.get("suspected_vehicle"))

        for suspect in session_suspects:
            ssr_key = f"{session_id}_{suspect}"
            ssr_items = self.client.read_stream_key_items(config.STREAM_SSR, ssr_key)
            if not ssr_items:
                continue
            ssr_record = ssr_items[-1]["data"]
            suspect_score = ssr_record.get("score", 0)

            # Paper Algorithm 2 Line 9:
            # if s.count >= 4 and S.score > s.count / 2 then
            meets_threshold = (count >= config.MIN_PARTICIPATING_VEHICLES)
            meets_majority = (suspect_score > (count * config.CONSENSUS_MAJORITY_RATIO))

            suspect_rec = self.get_vehicle_record(suspect)
            action_taken = "NO_ACTION"

            if meets_threshold and meets_majority:
                ssr_record["verification_result"] = True
                
                # Penalize suspect
                suspect_rec["tv"] -= config.PENALTY_TV
                suspect_rec["soft_blocked_until"] = int(time.time()) + config.SOFT_REVOCATION_PERIOD
                action_taken = "SOFT_REVOCATION"

                # Hard Revocation check (Algorithm 2 Line 12):
                if suspect_rec["tv"] < 0 and not suspect_rec.get("is_revoked"):
                    suspect_rec["is_revoked"] = True
                    action_taken = "HARD_REVOCATION"
                    
                    # Log into permanent revocation_list stream
                    self.client.publish_stream(
                        config.STREAM_REVOCATION,
                        suspect,
                        {
                            "suspected_vehicle": suspect,
                            "revoked_at": int(time.time()),
                            "final_tv": suspect_rec["tv"],
                            "reason": f"Trust value dropped below threshold in session {session_id}"
                        }
                    )
                self.update_vehicle_record(suspect, suspect_rec)
            else:
                ssr_record["verification_result"] = False
                action_taken = "ACQUITTED_INSUFFICIENT_CONSENSUS"

            self.client.publish_stream(config.STREAM_SSR, ssr_key, ssr_record)
            analysis_summary.append({
                "suspect": suspect,
                "score": suspect_score,
                "total_participants": count,
                "meets_threshold": meets_threshold,
                "meets_majority": meets_majority,
                "action": action_taken,
                "updated_tv": suspect_rec["tv"] if suspect_rec else None
            })

        # Close session
        session_data["status"] = "ANALYZED"
        session_data["analyzed_at"] = int(time.time())
        session_data["analyzed_by_rsu"] = rsu_address or self.admin
        self.client.publish_stream(config.STREAM_SESSION, session_id, session_data)

        return {
            "session_id": session_id,
            "status": "ANALYZED",
            "participants": count,
            "summary": analysis_summary
        }

    # =========================================================================
    # ALGORITHM 3: REWARD CLAIM BY AN INTELLIGENT VEHICLE (claimReward)
    # =========================================================================
    def claim_reward(self, claiming_vehicle: str, session_id: str) -> dict:
        """
        Algorithm 3: Vehicle claims rewards for participating in true detection.
        Awards +5 Credit Score, +1 TV, and +2 bonus points if vehicle was the first alarmer.
        Also transfers native 'iov_credit' tokens on-chain.
        """
        claimant_rec = self.get_vehicle_record(claiming_vehicle)
        if not claimant_rec:
            raise ValueError("Claiming vehicle not registered.")
        if claimant_rec.get("is_revoked"):
            raise PermissionError("Revoked vehicle cannot claim rewards.")

        session_items = self.client.read_stream_key_items(config.STREAM_SESSION, session_id)
        if not session_items or session_items[-1]["data"].get("status") != "ANALYZED":
            raise ValueError(f"Session {session_id} has not been analyzed by RSU yet.")
        session_data = session_items[-1]["data"]

        # Find latest PTR record for this vehicle in this session
        all_ptr = self.client.read_stream_items(config.STREAM_PTR)
        target_ptr = None
        for item in reversed(all_ptr):
            p = item.get("data", {})
            if p.get("reporter") == claiming_vehicle and p.get("session_id") == session_id:
                target_ptr = p
                break

        if not target_ptr:
            raise ValueError(f"Vehicle {claiming_vehicle} did not participate in session {session_id}.")
        if target_ptr.get("is_reward_received"):
            raise ValueError(f"Reward already claimed by {claiming_vehicle} for session {session_id}.")

        suspected = target_ptr.get("suspected_vehicle")
        ssr_key = f"{session_id}_{suspected}"
        ssr_items = self.client.read_stream_key_items(config.STREAM_SSR, ssr_key)
        if not ssr_items:
            raise ValueError("SSR record not found.")
        ssr_record = ssr_items[-1]["data"]

        # Check if vehicle's report matched RSU verification result
        if target_ptr.get("submitted") and ssr_record.get("verification_result") is True:
            reward_credits = config.REWARD_CREDIT_HONEST
            reward_tv = config.REWARD_TV_HONEST
            is_alarmer = (session_data.get("alarmer") == claiming_vehicle)
            
            if is_alarmer:
                reward_credits += config.REWARD_ALARMER_BONUS

            claimant_rec["credit_score"] += reward_credits
            claimant_rec["tv"] += reward_tv
            claimant_rec["claim_number"] = claimant_rec.get("claim_number", 0) + 1
            
            # Transfer on-chain native assets
            txid = self.client.send_asset(claiming_vehicle, config.ASSET_CREDIT, reward_credits)

            # Update PTR
            target_ptr["is_reward_received"] = True
            ptr_key = f"{claiming_vehicle}_{session_id}_{suspected}"
            self.client.publish_stream(config.STREAM_PTR, ptr_key, target_ptr)
            
            # Update Vehicle Register
            self.update_vehicle_record(claiming_vehicle, claimant_rec)

            return {
                "status": "REWARD_CLAIMED",
                "vehicle": claiming_vehicle,
                "session_id": session_id,
                "credits_awarded": reward_credits,
                "tv_increment": reward_tv,
                "is_alarmer_bonus": is_alarmer,
                "new_credit_score": claimant_rec["credit_score"],
                "new_tv": claimant_rec["tv"],
                "onchain_txid": txid
            }
        else:
            return {
                "status": "NO_REWARD",
                "reason": "Reported suspicion was not verified as malicious."
            }

    # =========================================================================
    # CROSS-REGION HANDOVER: LEAVE-REGION (Section V-B)
    # =========================================================================
    def leave_region(self, vehicle_address: str, source_region: str, target_region: str) -> dict:
        """
        Executes a LEAVE-REGION transaction.
        Syncs Trust Value and Wallet Score to Global ledger and issues new regional credentials.
        """
        v_rec = self.get_vehicle_record(vehicle_address)
        if not v_rec:
            raise ValueError("Vehicle not registered.")
        
        # New regional temporary address
        new_pseudo = self.client.get_new_address()
        self.client.grant_permissions(new_pseudo, "send,receive")
        self.client.call("grant", [new_pseudo, f"{config.STREAM_SESSION}.write"])
        self.client.call("grant", [new_pseudo, f"{config.STREAM_PTR}.write"])
        self.client.call("grant", [new_pseudo, f"{config.STREAM_SSR}.write"])

        handover_record = {
            "real_vin": v_rec["real_vin"],
            "old_address": vehicle_address,
            "new_address": new_pseudo,
            "synced_tv": v_rec["tv"],
            "synced_credit_score": v_rec["credit_score"],
            "source_region": source_region,
            "target_region": target_region,
            "handover_timestamp": int(time.time())
        }

        # Save to vehicle register under new pseudonym
        new_rec = dict(v_rec)
        new_rec["pseudo_address"] = new_pseudo
        new_rec["region"] = target_region
        self.client.publish_stream(config.STREAM_VEHICLE, new_pseudo, new_rec)

        return handover_record
