// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title GlobalTrustManager
 * @notice Global Blockchain Authority Contract from the paper:
 *         "Blockchain-Based Adaptive Trust Management in IoV Using Smart Contract"
 * @dev Governed by Traffic Authority (TA) and Certificate Authority (CA).
 *      Maintains permanent vehicle identities, pseudonyms, and global trust scores.
 */
contract GlobalTrustManager {
    address public trafficAuthority;
    address public certificateAuthority;

    struct GlobalVehicleRecord {
        bytes32 realVinHash;
        address currentPseudoAddress;
        int256 globalTrustValue;
        uint256 walletScore;
        bool isRevoked;
        uint256 registeredTimestamp;
    }

    // Mapping: Temporary Pseudonym => Global Record
    mapping(address => GlobalVehicleRecord) public globalRegistry;
    // Mapping: Real VIN Hash => Pseudonym Address
    mapping(bytes32 => address) public vinToPseudo;
    // Authorized Regional Authorities
    mapping(address => bool) public authorizedRegionalAuthorities;

    event VehicleRegistered(bytes32 indexed realVinHash, address indexed pseudoAddress, int256 initialTV);
    event GlobalScoreSynchronized(address indexed pseudoAddress, int256 updatedTV, uint256 updatedWalletScore);
    event VehiclePermanentlyRevoked(address indexed pseudoAddress, string reason);

    modifier onlyTA() {
        require(msg.sender == trafficAuthority, "Only Traffic Authority (TA) allowed.");
        _;
    }

    modifier onlyAuthorizedRA() {
        require(authorizedRegionalAuthorities[msg.sender] || msg.sender == trafficAuthority, "Caller is not authorized Regional Authority.");
        _;
    }

    constructor(address _certificateAuthority) {
        trafficAuthority = msg.sender;
        certificateAuthority = _certificateAuthority;
    }

    function addRegionalAuthority(address _ra) external onlyTA {
        authorizedRegionalAuthorities[_ra] = true;
    }

    function registerVehicle(
        bytes32 _realVinHash,
        address _pseudoAddress,
        int256 _initialTV
    ) external onlyTA {
        require(globalRegistry[_pseudoAddress].registeredTimestamp == 0, "Vehicle already registered with this pseudonym.");
        require(vinToPseudo[_realVinHash] == address(0), "VIN already registered.");

        globalRegistry[_pseudoAddress] = GlobalVehicleRecord({
            realVinHash: _realVinHash,
            currentPseudoAddress: _pseudoAddress,
            globalTrustValue: _initialTV,
            walletScore: 0,
            isRevoked: false,
            registeredTimestamp: block.timestamp
        });

        vinToPseudo[_realVinHash] = _pseudoAddress;
        emit VehicleRegistered(_realVinHash, _pseudoAddress, _initialTV);
    }

    function syncScoreFromRegion(
        address _pseudoAddress,
        int256 _updatedTV,
        uint256 _updatedWalletScore
    ) external onlyAuthorizedRA {
        require(globalRegistry[_pseudoAddress].registeredTimestamp > 0, "Vehicle not registered in global ledger.");
        
        GlobalVehicleRecord storage record = globalRegistry[_pseudoAddress];
        record.globalTrustValue = _updatedTV;
        record.walletScore = _updatedWalletScore;

        if (_updatedTV < 0) {
            record.isRevoked = true;
            emit VehiclePermanentlyRevoked(_pseudoAddress, "Trust Value fell below zero (Hard Revocation).");
        }

        emit GlobalScoreSynchronized(_pseudoAddress, _updatedTV, _updatedWalletScore);
    }

    function getVehicleRecord(address _pseudoAddress) external view returns (GlobalVehicleRecord memory) {
        return globalRegistry[_pseudoAddress];
    }
}
