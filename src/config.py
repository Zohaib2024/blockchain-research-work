"""
ZohaibChain1 Configuration File
Holds MultiChain RPC connection parameters, stream mappings, and paper-specific IoV constants.
"""

RPC_URL = "http://127.0.0.1:4344"
RPC_USER = "multichainrpc"
RPC_PASS = "HjPFZ7ujgvtbvzJo4SWrsQakSwcK9Y4oTsw3hXhZHqSK"
CHAIN_NAME = "zohaibchain1"

# Primary authority address (Traffic Authority / RSU Leader)
ADMIN_ADDRESS = "1HcFCQ4wT43ko7KaXmX6vzyifviNgZDYUNwG8d"

# Stream Identifiers (Paper Registers)
STREAM_SESSION = "session_register"
STREAM_PTR = "ptr_stream"
STREAM_SSR = "ssr_stream"
STREAM_VEHICLE = "vehicle_register"
STREAM_REVOCATION = "revocation_list"

# Native Asset
ASSET_CREDIT = "iov_credit"

# Paper Evaluation Constants (Section V-B & Algorithms 1-3)
MIN_PARTICIPATING_VEHICLES = 4   # Minimum 4 vehicles required to avoid framing attacks
CONSENSUS_MAJORITY_RATIO = 0.50  # Must be strictly > s.count / 2 (majority rule)
REWARD_CREDIT_HONEST = 5         # +5 credit points for true report
REWARD_TV_HONEST = 1             # +1 Trust Value for true report
REWARD_ALARMER_BONUS = 2         # +2 additional points for first alarmer vehicle
PENALTY_TV = 1                   # -1 Trust Value for detected malicious peer
SOFT_REVOCATION_PERIOD = 60      # Blocked for 60 seconds (1 minute)
INITIAL_TRUST_VALUE = 3          # Starting TV for registered vehicles
