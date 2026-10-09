"""
Unit Test Suite for IoV Adaptive Trust Management on ZohaibChain1
Verifies paper requirements mapped to Graduate Blockchain Coursework:
- Test 1 [GoofyCoin & ScroogeCoin Principles]: Algorithm 1 Event Reporting & Double-Voting Prevention
- Test 2 [Bitcoin Transactions & Scripts]: Algorithm 2 RSU Edge Consensus & Multisig Quorum Enforcement (>= 4 Witnesses)
- Test 3 [Cryptography & Blockchain Basics]: Algorithm 3 Native Token Distribution (iov_credit) & Economic Incentives
- Test 4 [Bitcoin Consensus & Mining]: Solo Framing Attack Rejection via Quorum Defense
"""

import unittest
import time
from src.multichain_client import MultiChainClient
from src.iov_trust_manager import IoVTrustManager
from src import config

class TestIoVTrustAlgorithms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = MultiChainClient()
        cls.manager = IoVTrustManager(cls.client)

        # Register test vehicles
        cls.v_alarmer = cls.manager.register_vehicle("VIN-TEST-ALARMER", initial_tv=3)
        cls.v_peer1   = cls.manager.register_vehicle("VIN-TEST-PEER1", initial_tv=3)
        cls.v_peer2   = cls.manager.register_vehicle("VIN-TEST-PEER2", initial_tv=3)
        cls.v_peer3   = cls.manager.register_vehicle("VIN-TEST-PEER3", initial_tv=3)
        cls.v_rogue   = cls.manager.register_vehicle("VIN-TEST-ROGUE", initial_tv=1)

    def test_01_algorithm1_reporting_and_duplicate_prevention(self):
        """Test Algorithm 1 reporting and ensuring duplicate votes are rejected."""
        session_id = f"TEST_SES_{int(time.time())}_1"
        
        # Initial report
        res = self.manager.report_suspicion(
            session_id,
            self.v_alarmer["pseudo_address"],
            self.v_rogue["pseudo_address"]
        )
        self.assertEqual(res["status"], "SUSPICION_RECORDED")
        self.assertEqual(res["participating_count"], 1)

        # Duplicate attempt by the same vehicle in same session must fail
        with self.assertRaises(ValueError) as ctx:
            self.manager.report_suspicion(
                session_id,
                self.v_alarmer["pseudo_address"],
                self.v_rogue["pseudo_address"]
            )
        self.assertIn("Duplicate report", str(ctx.exception))

    def test_02_algorithm2_rsu_consensus_and_penalty(self):
        """Test Algorithm 2 majority voting and soft revocation when count >= 4."""
        session_id = f"TEST_SES_{int(time.time())}_2"
        
        # 4 vehicles report the rogue vehicle
        self.manager.report_suspicion(session_id, self.v_alarmer["pseudo_address"], self.v_rogue["pseudo_address"])
        self.manager.report_suspicion(session_id, self.v_peer1["pseudo_address"], self.v_rogue["pseudo_address"])
        self.manager.report_suspicion(session_id, self.v_peer2["pseudo_address"], self.v_rogue["pseudo_address"])
        self.manager.report_suspicion(session_id, self.v_peer3["pseudo_address"], self.v_rogue["pseudo_address"])

        # RSU analyzes
        analysis = self.manager.analyse_reports(session_id)
        self.assertEqual(analysis["status"], "ANALYZED")
        self.assertEqual(analysis["participants"], 4)
        
        summary = analysis["summary"][0]
        self.assertTrue(summary["meets_threshold"])
        self.assertTrue(summary["meets_majority"])
        self.assertEqual(summary["action"], "SOFT_REVOCATION")
        self.assertEqual(summary["updated_tv"], 0)

    def test_03_algorithm3_reward_claims(self):
        """Test Algorithm 3 claims: alarmer gets +7 (5+2), peers get +5."""
        session_id = f"TEST_SES_{int(time.time())}_3"
        
        # Setup session with 4 honest reporters
        self.manager.report_suspicion(session_id, self.v_alarmer["pseudo_address"], self.v_rogue["pseudo_address"])
        self.manager.report_suspicion(session_id, self.v_peer1["pseudo_address"], self.v_rogue["pseudo_address"])
        self.manager.report_suspicion(session_id, self.v_peer2["pseudo_address"], self.v_rogue["pseudo_address"])
        self.manager.report_suspicion(session_id, self.v_peer3["pseudo_address"], self.v_rogue["pseudo_address"])

        self.manager.analyse_reports(session_id)

        # Alarmer claim (should get 5 + 2 = 7)
        alarmer_res = self.manager.claim_reward(self.v_alarmer["pseudo_address"], session_id)
        self.assertEqual(alarmer_res["credits_awarded"], 7)
        self.assertTrue(alarmer_res["is_alarmer_bonus"])

        # Peer 1 claim (should get 5)
        peer1_res = self.manager.claim_reward(self.v_peer1["pseudo_address"], session_id)
        self.assertEqual(peer1_res["credits_awarded"], 5)
        self.assertFalse(peer1_res["is_alarmer_bonus"])

        # Double claim prevention
        with self.assertRaises(ValueError) as ctx:
            self.manager.claim_reward(self.v_alarmer["pseudo_address"], session_id)
        self.assertIn("already claimed", str(ctx.exception))

    def test_04_solo_framing_attack_rejection(self):
        """Test that single rogue vehicle cannot frame an innocent peer (Threshold < 4)."""
        session_id = f"TEST_SES_{int(time.time())}_4"
        
        # Only 1 vehicle reports
        self.manager.report_suspicion(session_id, self.v_peer1["pseudo_address"], self.v_peer2["pseudo_address"])

        analysis = self.manager.analyse_reports(session_id)
        summary = analysis["summary"][0]
        self.assertFalse(summary["meets_threshold"])
        self.assertEqual(summary["action"], "ACQUITTED_INSUFFICIENT_CONSENSUS")

if __name__ == "__main__":
    unittest.main()
