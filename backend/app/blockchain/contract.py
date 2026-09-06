"""Smart contract ABI and interface."""

CONTRACT_ABI = [
    {"anonymous": False, "inputs": [
        {"indexed": True, "internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
        {"indexed": True, "internalType": "address", "name": "anchor", "type": "address"},
        {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
    ], "name": "EvidenceAnchored", "type": "event"},
    {"anonymous": False, "inputs": [
        {"indexed": True, "internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
        {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        {"indexed": False, "internalType": "address", "name": "anchor", "type": "address"}
    ], "name": "EvidenceVerified", "type": "event"},
    {"inputs": [{"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"}],
     "name": "anchorEvidence", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
     "name": "evidence", "outputs": [
        {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        {"internalType": "address", "name": "anchor", "type": "address"},
        {"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"}
    ], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
     "name": "evidenceList", "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getEvidenceCount",
     "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"}],
     "name": "verifyEvidence", "outputs": [
        {"internalType": "bool", "name": "exists", "type": "bool"},
        {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        {"internalType": "address", "name": "anchor", "type": "address"}
    ], "stateMutability": "view", "type": "function"}
]
