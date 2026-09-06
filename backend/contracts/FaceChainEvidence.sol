// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title FaceChainEvidence
 * @notice Minimal evidence anchoring contract for FaceChain Goa
 * @dev Stores SHA-256 evidence hashes on Ethereum Sepolia testnet
 */
contract FaceChainEvidence {

    struct Evidence {
        uint256 timestamp;
        address anchor;
        bytes32 evidenceHash;
    }

    mapping(bytes32 => Evidence) public evidence;
    bytes32[] public evidenceList;

    event EvidenceAnchored(
        bytes32 indexed evidenceHash,
        address indexed anchor,
        uint256 timestamp
    );

    event EvidenceVerified(
        bytes32 indexed evidenceHash,
        uint256 timestamp,
        address anchor
    );

    /**
     * @notice Anchor a new evidence hash on-chain
     * @param evidenceHash SHA-256 hash of the evidence
     */
    function anchorEvidence(bytes32 evidenceHash) external {
        require(evidenceHash != bytes32(0), "Invalid hash");
        require(evidence[evidenceHash].timestamp == 0, "Evidence already anchored");

        evidence[evidenceHash] = Evidence({
            timestamp: block.timestamp,
            anchor: msg.sender,
            evidenceHash: evidenceHash
        });
        evidenceList.push(evidenceHash);

        emit EvidenceAnchored(evidenceHash, msg.sender, block.timestamp);
    }

    /**
     * @notice Verify if evidence hash exists on-chain
     * @param evidenceHash SHA-256 hash to verify
     * @return exists Whether the evidence exists
     * @return timestamp Block timestamp of anchoring
     * @return anchor Address that anchored the evidence
     */
    function verifyEvidence(bytes32 evidenceHash) 
        external 
        view 
        returns (bool exists, uint256 timestamp, address anchor) 
    {
        Evidence storage e = evidence[evidenceHash];
        if (e.timestamp == 0) {
            return (false, 0, address(0));
        }
        return (true, e.timestamp, e.anchor);
    }

    /**
     * @notice Get total number of anchored evidences
     */
    function getEvidenceCount() external view returns (uint256) {
        return evidenceList.length;
    }
}
