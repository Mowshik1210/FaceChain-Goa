"""Configuration management for FaceChain Goa."""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class FaceConfig:
    model: str = os.getenv("FACE_MODEL", "Facenet512")
    detector: str = os.getenv("FACE_DETECTOR", "retinaface")
    match_threshold: float = float(os.getenv("MATCH_THRESHOLD", "0.65"))
    min_face_size: int = 80
    min_confidence: float = 0.85
    min_sharpness: float = 30.0


@dataclass
class SearchConfig:
    provider: str = os.getenv("SEARCH_PROVIDER", "duckduckgo")
    api_key: Optional[str] = os.getenv("SEARCH_API_KEY")
    max_candidates: int = 10
    timeout_seconds: int = 30
    max_download_size_mb: int = 10


@dataclass
class BlockchainConfig:
    network: str = os.getenv("BLOCKCHAIN_NETWORK", "sepolia")
    rpc_url: Optional[str] = os.getenv("BLOCKCHAIN_RPC_URL")
    private_key: Optional[str] = os.getenv("BLOCKCHAIN_PRIVATE_KEY")
    contract_address: Optional[str] = os.getenv("BLOCKCHAIN_CONTRACT_ADDRESS")
    gas_limit: int = 300000
    max_fee_per_gas_gwei: float = 50.0
    confirmation_blocks: int = 1


@dataclass
class AppConfig:
    face: FaceConfig = None
    search: SearchConfig = None
    blockchain: BlockchainConfig = None
    demo_image_path: str = os.getenv("DEMO_IMAGE_PATH", "data/demo/sample.jpg")
    temp_dir: str = "tmp"
    max_faces_per_image: int = 5

    def __post_init__(self):
        if self.face is None:
            self.face = FaceConfig()
        if self.search is None:
            self.search = SearchConfig()
        if self.blockchain is None:
            self.blockchain = BlockchainConfig()
        os.makedirs(self.temp_dir, exist_ok=True)


config = AppConfig()
