"""Blockchain client for evidence anchoring."""
import time
from typing import Optional, Tuple
from web3 import Web3
from eth_account import Account
from app.models import BlockchainRecord
from app.config import config
from app.blockchain.contract import CONTRACT_ABI


class BlockchainClient:
    def __init__(self):
        self.network = config.blockchain.network
        self.rpc_url = config.blockchain.rpc_url
        self.private_key = config.blockchain.private_key
        self.contract_address = config.blockchain.contract_address
        self.gas_limit = config.blockchain.gas_limit
        self.max_fee_gwei = config.blockchain.max_fee_per_gas_gwei
        self.confirmation_blocks = config.blockchain.confirmation_blocks
        self.w3 = None
        self.account = None
        self.contract = None
        self._initialized = False

    def is_configured(self) -> bool:
        return (self.rpc_url and len(self.rpc_url) > 0 and
                self.private_key and len(self.private_key) > 0)

    def initialize(self) -> bool:
        if not self.is_configured():
            return False
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            if not self.w3.is_connected():
                raise ConnectionError("Could not connect to RPC")
            self.account = Account.from_key(self.private_key)
            if self.contract_address:
                self.contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(self.contract_address),
                    abi=CONTRACT_ABI
                )
            self._initialized = True
            return True
        except Exception as e:
            print(f"Blockchain initialization failed: {e}")
            return False

    def get_balance(self) -> float:
        if not self._initialized:
            return 0.0
        balance_wei = self.w3.eth.get_balance(self.account.address)
        return self.w3.from_wei(balance_wei, "ether")

    def anchor_evidence(self, evidence_hash: str) -> Optional[BlockchainRecord]:
        if not self._initialized:
            raise RuntimeError("Blockchain client not initialized")
        if not evidence_hash.startswith("0x"):
            evidence_hash = "0x" + evidence_hash
        evidence_bytes32 = Web3.to_bytes(hexstr=evidence_hash).ljust(32, b'\x00')
        try:
            if self.contract:
                tx = self.contract.functions.anchorEvidence(evidence_bytes32).build_transaction({
                    "from": self.account.address,
                    "nonce": self.w3.eth.get_transaction_count(self.account.address),
                    "gas": self.gas_limit,
                    "maxFeePerGas": self.w3.to_wei(self.max_fee_gwei, "gwei"),
                    "maxPriorityFeePerGas": self.w3.to_wei(1, "gwei"),
                    "chainId": self.w3.eth.chain_id
                })
            else:
                tx = {
                    "to": self.account.address, "value": 0, "gas": 21000,
                    "maxFeePerGas": self.w3.to_wei(self.max_fee_gwei, "gwei"),
                    "maxPriorityFeePerGas": self.w3.to_wei(1, "gwei"),
                    "nonce": self.w3.eth.get_transaction_count(self.account.address),
                    "data": evidence_hash, "chainId": self.w3.eth.chain_id
                }
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120, poll_latency=2)
            if receipt["status"] != 1:
                raise RuntimeError("Transaction failed")
            return BlockchainRecord(
                network=self.network, tx_hash=tx_hash.hex(),
                block_number=receipt["blockNumber"], gas_used=receipt["gasUsed"],
                timestamp=int(time.time()), contract_address=self.contract_address,
                evidence_hash=evidence_hash
            )
        except Exception as e:
            raise RuntimeError(f"Blockchain anchoring failed: {e}")

    def verify_on_chain(self, evidence_hash: str) -> Tuple[bool, Optional[dict]]:
        if not self._initialized:
            return False, None
        if not evidence_hash.startswith("0x"):
            evidence_hash = "0x" + evidence_hash
        evidence_bytes32 = Web3.to_bytes(hexstr=evidence_hash).ljust(32, b'\x00')
        try:
            if self.contract:
                exists, timestamp, anchor = self.contract.functions.verifyEvidence(evidence_bytes32).call()
                return exists, {"timestamp": timestamp, "anchor": anchor, "exists": exists}
            return False, None
        except Exception as e:
            print(f"On-chain verification error: {e}")
            return False, None

    def get_explorer_url(self, tx_hash: str) -> str:
        if self.network == "sepolia":
            return f"https://sepolia.etherscan.io/tx/{tx_hash}"
        elif self.network == "goerli":
            return f"https://goerli.etherscan.io/tx/{tx_hash}"
        elif self.network == "mainnet":
            return f"https://etherscan.io/tx/{tx_hash}"
        else:
            return f"https://{self.network}.etherscan.io/tx/{tx_hash}"
