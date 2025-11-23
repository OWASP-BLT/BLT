"""
Reward Distribution Service for Bug Bounty Rewards

This module handles automatic distribution of bug bounty rewards using the
Ethereum smart contract. It provides functions to interact with the blockchain
and manage reward distributions.
"""

import logging
from decimal import Decimal
from typing import Optional, Tuple

from django.conf import settings
from web3 import Web3
from web3.exceptions import Web3Exception

logger = logging.getLogger(__name__)


class RewardDistributionService:
    """Service for interacting with the BugBountyReward smart contract"""

    def __init__(self):
        """Initialize the Web3 connection and smart contract interface"""
        self.enabled = self._check_configuration()
        if not self.enabled:
            logger.warning("Reward distribution service is disabled due to missing configuration")
            return

        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_NODE_URL))

        # Load contract ABI and address
        self.contract_address = settings.CONTRACT_ADDRESS
        self.contract_abi = self._load_contract_abi()

        # Initialize contract
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.contract_abi)

        # Load account for signing transactions
        self.account = self.w3.eth.account.from_key(settings.ETHEREUM_PRIVATE_KEY)

    def _check_configuration(self) -> bool:
        """Check if all required configuration is present"""
        required_settings = ["ETHEREUM_NODE_URL", "CONTRACT_ADDRESS", "ETHEREUM_PRIVATE_KEY"]
        for setting in required_settings:
            if not hasattr(settings, setting) or not getattr(settings, setting):
                logger.warning(f"Missing required setting: {setting}")
                return False
        return True

    def _load_contract_abi(self) -> list:
        """Load the smart contract ABI"""
        # This is a simplified ABI with the functions we need
        # In production, this should be loaded from the compiled contract JSON
        return [
            {
                "inputs": [
                    {"internalType": "uint256", "name": "_huntId", "type": "uint256"},
                    {"internalType": "uint256", "name": "_issueId", "type": "uint256"},
                    {"internalType": "address payable", "name": "_hunter", "type": "address"},
                    {"internalType": "uint256", "name": "_amount", "type": "uint256"},
                ],
                "name": "distributeReward",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "uint256", "name": "_huntId", "type": "uint256"}],
                "name": "getHuntRewardPool",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "_huntId", "type": "uint256"},
                    {"internalType": "uint256", "name": "_issueId", "type": "uint256"},
                ],
                "name": "isIssueRewarded",
                "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "_huntId", "type": "uint256"},
                    {"internalType": "address", "name": "_organization", "type": "address"},
                ],
                "name": "createHunt",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "uint256", "name": "_huntId", "type": "uint256"}],
                "name": "fundHunt",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function",
            },
        ]

    def distribute_reward(
        self, hunt_id: int, issue_id: int, hunter_address: str, amount_usd: Decimal
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Distribute a reward to a bug hunter

        Args:
            hunt_id: ID of the bug hunt
            issue_id: ID of the approved issue
            hunter_address: Ethereum address of the hunter
            amount_usd: Reward amount in USD

        Returns:
            Tuple of (success, transaction_hash, error_message)
        """
        if not self.enabled:
            return False, None, "Reward distribution service is not configured"

        try:
            # Validate hunter address
            if not Web3.is_address(hunter_address):
                return False, None, f"Invalid Ethereum address: {hunter_address}"

            # Convert USD to Wei (ETH smallest unit)
            # In production, use a price oracle like Chainlink
            amount_wei = self._usd_to_wei(amount_usd)

            # Check if issue was already rewarded
            if self.is_issue_rewarded(hunt_id, issue_id):
                return False, None, "Issue has already been rewarded on blockchain"

            # Check hunt reward pool balance
            pool_balance = self.get_hunt_reward_pool(hunt_id)
            if pool_balance < amount_wei:
                return (
                    False,
                    None,
                    f"Insufficient reward pool balance. Required: {amount_wei}, Available: {pool_balance}",
                )

            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            transaction = self.contract.functions.distributeReward(
                hunt_id, issue_id, Web3.to_checksum_address(hunter_address), amount_wei
            ).build_transaction(
                {
                    "from": self.account.address,
                    "nonce": nonce,
                    "gas": 200000,  # Estimate gas
                    "gasPrice": self.w3.eth.gas_price,
                }
            )

            # Sign transaction
            signed_txn = self.account.sign_transaction(transaction)

            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            # Wait for transaction receipt (with timeout)
            # Configurable timeout for different network conditions
            timeout = getattr(settings, "BLOCKCHAIN_TX_TIMEOUT", 120)
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)

            if tx_receipt["status"] == 1:
                tx_hash_hex = tx_hash.hex()
                logger.info(
                    f"Reward distributed successfully. Hunt: {hunt_id}, Issue: {issue_id}, TX: {tx_hash_hex}"
                )
                return True, tx_hash_hex, None
            else:
                logger.error(f"Transaction failed. Receipt: {tx_receipt}")
                return False, None, "Transaction failed on blockchain"

        except Web3Exception as e:
            logger.error(f"Web3 error distributing reward: {str(e)}", exc_info=True)
            return False, None, f"Blockchain error: {str(e)}"
        except Exception as e:
            logger.error(f"Error distributing reward: {str(e)}", exc_info=True)
            return False, None, f"Unexpected error: {str(e)}"

    def is_issue_rewarded(self, hunt_id: int, issue_id: int) -> bool:
        """
        Check if an issue has already been rewarded

        Args:
            hunt_id: ID of the bug hunt
            issue_id: ID of the issue

        Returns:
            True if issue was rewarded, False otherwise
        """
        if not self.enabled:
            return False

        try:
            return self.contract.functions.isIssueRewarded(hunt_id, issue_id).call()
        except Exception as e:
            logger.error(f"Error checking if issue is rewarded: {str(e)}")
            return False

    def get_hunt_reward_pool(self, hunt_id: int) -> int:
        """
        Get the current reward pool balance for a hunt

        Args:
            hunt_id: ID of the bug hunt

        Returns:
            Balance in Wei
        """
        if not self.enabled:
            return 0

        try:
            return self.contract.functions.getHuntRewardPool(hunt_id).call()
        except Exception as e:
            logger.error(f"Error getting hunt reward pool: {str(e)}")
            return 0

    def _usd_to_wei(self, amount_usd: Decimal) -> int:
        """
        Convert USD amount to Wei (ETH smallest unit)

        In production, this should use a price oracle like Chainlink
        For now, using a placeholder conversion rate

        Args:
            amount_usd: Amount in USD

        Returns:
            Amount in Wei
        """
        # WARNING: This uses a static ETH price which can lead to incorrect reward amounts!
        # TODO: Replace with real-time price from oracle (e.g., Chainlink) before production
        # For testing: Update ETH_PRICE_USD in settings regularly to match market price
        # For production: Integrate Chainlink or similar price oracle
        eth_price_usd = Decimal(getattr(settings, "ETH_PRICE_USD", "2000"))
        amount_eth = amount_usd / eth_price_usd
        amount_wei = int(amount_eth * Decimal("1000000000000000000"))  # 1 ETH = 10^18 Wei
        return amount_wei

    def create_hunt(self, hunt_id: int, organization_address: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Create a new hunt on the blockchain

        Args:
            hunt_id: ID of the bug hunt
            organization_address: Ethereum address of the organization

        Returns:
            Tuple of (success, transaction_hash, error_message)
        """
        if not self.enabled:
            return False, None, "Reward distribution service is not configured"

        try:
            # Validate organization address
            if not Web3.is_address(organization_address):
                return False, None, f"Invalid Ethereum address: {organization_address}"

            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            transaction = self.contract.functions.createHunt(
                hunt_id, Web3.to_checksum_address(organization_address)
            ).build_transaction(
                {
                    "from": self.account.address,
                    "nonce": nonce,
                    "gas": 150000,
                    "gasPrice": self.w3.eth.gas_price,
                }
            )

            # Sign and send transaction
            signed_txn = self.account.sign_transaction(transaction)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            # Wait for receipt
            timeout = getattr(settings, "BLOCKCHAIN_TX_TIMEOUT", 120)
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)

            if tx_receipt["status"] == 1:
                tx_hash_hex = tx_hash.hex()
                logger.info(f"Hunt created successfully. Hunt: {hunt_id}, TX: {tx_hash_hex}")
                return True, tx_hash_hex, None
            else:
                return False, None, "Transaction failed on blockchain"

        except Exception as e:
            logger.error(f"Error creating hunt: {str(e)}", exc_info=True)
            return False, None, str(e)


# Singleton instance
_reward_service = None


def get_reward_service() -> RewardDistributionService:
    """Get or create the reward distribution service instance"""
    global _reward_service
    if _reward_service is None:
        _reward_service = RewardDistributionService()
    return _reward_service
