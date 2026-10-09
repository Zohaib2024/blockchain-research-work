// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title RegionalTrustManager
 * @notice Implements Algorithms 1, 2, and 3 from:
 *         "Blockchain-Based Adaptive Trust Management in IoV Using Smart Contract"
 * @dev Deployed on Regional Sharded Blockchains (Edge RSU Plane).
 */
contract RegionalTrustManager {
    address public regionalAuthority;
    
    // Constant parameters from Section V-B
    uint256 public constant MIN_PARTICIPANTS = 4;
    uint256 public constant REWARD_CREDIT_HONEST = 5;
    int256 public constant REWARD_TV_HONEST = 1;
    uint256 public constant REWARD_ALARMER_BONUS = 2;
    int256 public constant PENALTY_TV = 1;
    uint256 public constant SOFT_BLOCK_DURATION = 60 seconds;

    // Registers from Paper Section V-B
    struct VehicleRecord {
        address registeredAddress;
        int256 tv;                  // Trust Value
        uint256 creditScore;        // Wallet points
        bool isRevoked;             // Hard revocation
        uint256 softBlockedUntil;   // Soft revocation timeout
        uint256 reportNumber;
        uint256 claimNumber;
        bool isEnrolled;
    }

    struct SessionRecord {
        uint256 sessionId;
        address alarmer;
        uint256 count;
        address[] participants;
        bool isAnalyzed;
    }

    struct PersonalTxRecord {
        address reporter;
        uint256 sessionId;
        address suspectedVehicle;
        bool submitted;
        bool isRewardReceived;
    }

    struct ScoreStatusRecord {
        uint256 sessionId;
        address suspectedVehicle;
        uint256 score;
        bool isVerified;
    }

    // Storage Mappings (Smart Contract Registers)
    mapping(address => VehicleRecord) public VR;                                         // Vehicle Register
    mapping(uint256 => SessionRecord) public sessionRegister;                            // Session Register
    mapping(address => mapping(uint256 => mapping(address => PersonalTxRecord))) public PTR; // PTR
    mapping(uint256 => mapping(address => ScoreStatusRecord)) public SSR;                // SSR
    mapping(address => bool) public authorizedRSUs;                                      // Authorized RSU edge miners
    mapping(address => bool) public revocationList;                                      // Hard Revocation List

    // Events
    event SuspicionReported(uint256 indexed sessionId, address indexed reporter, address indexed suspected, uint256 count);
    event ReportsAnalyzed(uint256 indexed sessionId, address indexed suspected, bool verified, int256 newTV, string action);
    event RewardClaimed(address indexed claimant, uint256 indexed sessionId, uint256 creditsAwarded, int256 newTV);
    event VehicleRevoked(address indexed vehicle, string reason);
    event RegionHandover(address indexed oldAddress, address indexed newAddress, int256 tv, uint256 creditScore);

    // Modifiers matching Figure 7 from paper
    modifier onlyRA() {
        require(msg.sender == regionalAuthority, "Only Regional Authority allowed.");
        _;
    }

    modifier onlyRSU() {
        require(authorizedRSUs[msg.sender] || msg.sender == regionalAuthority, "Caller must be an authorized RSU.");
        _;
    }

    modifier onlyIntelligentVehicle() {
        require(VR[msg.sender].isEnrolled, "Caller is not an enrolled Intelligent Vehicle.");
        require(!VR[msg.sender].isRevoked, "Caller is permanently revoked.");
        require(block.timestamp >= VR[msg.sender].softBlockedUntil, "Caller is temporarily soft-blocked.");
        _;
    }

    constructor() {
        regionalAuthority = msg.sender;
        authorizedRSUs[msg.sender] = true;
    }

    function configureRSU(address _rsu, bool _status) external onlyRA {
        authorizedRSUs[_rsu] = _status;
    }

    function enrollVehicle(address _vehicle, int256 _initialTV) external onlyRA {
        require(!VR[_vehicle].isEnrolled, "Vehicle already enrolled.");
        VR[_vehicle] = VehicleRecord({
            registeredAddress: _vehicle,
            tv: _initialTV,
            creditScore: 0,
            isRevoked: false,
            softBlockedUntil: 0,
            reportNumber: 0,
            claimNumber: 0,
            isEnrolled: true
        });
    }

    // =========================================================================
    // ALGORITHM 1: Handle Reporting of an Event
    // =========================================================================
    function reportSuspicion(uint256 x, address suspectedVehicle) external onlyIntelligentVehicle {
        require(VR[suspectedVehicle].isEnrolled, "Suspected vehicle is not registered.");
        require(msg.sender != suspectedVehicle, "Cannot report oneself.");

        SessionRecord storage s = sessionRegister[x];

        // If new session, initialize alarmer
        if (s.count == 0) {
            s.sessionId = x;
            s.alarmer = msg.sender;
            s.count = 1;
            s.participants.push(msg.sender);
            s.isAnalyzed = false;
        } else {
            require(!s.isAnalyzed, "Session has already been analyzed.");
            // Check for duplicate submission
            PersonalTxRecord storage existingPtr = PTR[msg.sender][x][suspectedVehicle];
            require(!existingPtr.submitted, "Duplicate report: already reported in this session.");
            
            s.count += 1;
            s.participants.push(msg.sender);
        }

        // Update PTR
        PTR[msg.sender][x][suspectedVehicle] = PersonalTxRecord({
            reporter: msg.sender,
            sessionId: x,
            suspectedVehicle: suspectedVehicle,
            submitted: true,
            isRewardReceived: false
        });

        // Update SSR
        ScoreStatusRecord storage ssr = SSR[x][suspectedVehicle];
        ssr.sessionId = x;
        ssr.suspectedVehicle = suspectedVehicle;
        ssr.score += 1;

        VR[msg.sender].reportNumber += 1;
        emit SuspicionReported(x, msg.sender, suspectedVehicle, s.count);
    }

    // =========================================================================
    // ALGORITHM 2: Analyzing Report and Trust Update
    // =========================================================================
    function analyseReports(uint256 x, address suspectedVehicle) external onlyRSU {
        SessionRecord storage s = sessionRegister[x];
        require(s.count > 0, "Session does not exist.");
        require(!s.isAnalyzed, "Session reports already analyzed.");

        ScoreStatusRecord storage ssr = SSR[x][suspectedVehicle];
        VehicleRecord storage vSuspect = VR[suspectedVehicle];

        // Algorithm 2 Line 9:
        // if s.count >= 4 and S.score > s.count / 2 then
        if (s.count >= MIN_PARTICIPANTS && ssr.score > (s.count / 2)) {
            ssr.isVerified = true;
            vSuspect.tv -= PENALTY_TV;
            vSuspect.softBlockedUntil = block.timestamp + SOFT_BLOCK_DURATION;

            // Algorithm 2 Line 12:
            // if v.TV < 0 and v.Revoked != true then
            if (vSuspect.tv < 0 && !vSuspect.isRevoked) {
                vSuspect.isRevoked = true;
                revocationList[suspectedVehicle] = true;
                emit VehicleRevoked(suspectedVehicle, "Trust value fell below 0 (Hard Revocation).");
            }
            emit ReportsAnalyzed(x, suspectedVehicle, true, vSuspect.tv, "PUNISHED_SOFT_REVOCATION");
        } else {
            ssr.isVerified = false;
            emit ReportsAnalyzed(x, suspectedVehicle, false, vSuspect.tv, "ACQUITTED_INSUFFICIENT_EVIDENCE");
        }

        s.isAnalyzed = true;
    }

    // =========================================================================
    // ALGORITHM 3: Reward Claim by an Intelligent Vehicle
    // =========================================================================
    function claimReward(uint256 x, address suspectedVehicle) external onlyIntelligentVehicle {
        SessionRecord storage s = sessionRegister[x];
        require(s.isAnalyzed, "Session reports are not yet analyzed by RSU.");

        PersonalTxRecord storage p = PTR[msg.sender][x][suspectedVehicle];
        require(p.submitted, "No submission record found for caller in this session.");
        require(!p.isRewardReceived, "Reward has already been claimed.");

        ScoreStatusRecord storage ssr = SSR[x][suspectedVehicle];

        // Algorithm 3 Line 11:
        // if P.submitted == S.verificationResult then
        if (p.submitted && ssr.isVerified) {
            uint256 awardedCredits = REWARD_CREDIT_HONEST;
            VR[msg.sender].tv += REWARD_TV_HONEST;

            // Algorithm 3 Line 15:
            // if s.alarmer == msg.sender then
            if (s.alarmer == msg.sender) {
                awardedCredits += REWARD_ALARMER_BONUS;
            }

            VR[msg.sender].creditScore += awardedCredits;
            VR[msg.sender].claimNumber += 1;
            p.isRewardReceived = true;

            emit RewardClaimed(msg.sender, x, awardedCredits, VR[msg.sender].tv);
        }
    }

    // =========================================================================
    // REGIONAL HANDOVER: LEAVE-REGION
    // =========================================================================
    function leaveRegion(address newPseudoAddress) external onlyIntelligentVehicle {
        require(newPseudoAddress != address(0), "Invalid new address.");
        VehicleRecord memory oldRec = VR[msg.sender];

        // Enroll new temporary identity with preserved TV and credit score
        VR[newPseudoAddress] = VehicleRecord({
            registeredAddress: newPseudoAddress,
            tv: oldRec.tv,
            creditScore: oldRec.creditScore,
            isRevoked: false,
            softBlockedUntil: 0,
            reportNumber: 0,
            claimNumber: 0,
            isEnrolled: true
        });

        // De-enroll old temporary identity
        VR[msg.sender].isEnrolled = false;
        emit RegionHandover(msg.sender, newPseudoAddress, oldRec.tv, oldRec.creditScore);
    }
}
