"""
Tests for the automatic reward distribution system
"""

from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from website.models import Domain, Hunt, HuntPrize, Issue, UserProfile
from website.services.reward_distribution import RewardDistributionService, get_reward_service


class RewardDistributionServiceTestCase(TestCase):
    """Test cases for the RewardDistributionService"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(username="testhunter", email="hunter@test.com", password="testpass123")

        # Create user profile with ETH address
        self.user_profile = UserProfile.objects.get(user=self.user)
        self.user_profile.eth_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        self.user_profile.preferred_cryptocurrency = "ETH"
        self.user_profile.save()

        # Create domain
        self.domain = Domain.objects.create(name="example.com", url="https://example.com")

        # Create hunt
        self.hunt = Hunt.objects.create(
            domain=self.domain, name="Test Hunt", description="Test hunt description", starts_on=timezone.now()
        )

        # Create hunt prize
        self.prize = HuntPrize.objects.create(hunt=self.hunt, name="First Prize", value=100)

        # Create issue
        self.issue = Issue.objects.create(
            user=self.user,
            hunt=self.hunt,
            domain=self.domain,
            url="https://example.com/test",
            description="Test bug",
            verified=False,
        )

    @override_settings(
        ETHEREUM_NODE_URL="",
        CONTRACT_ADDRESS="",
        ETHEREUM_PRIVATE_KEY="",
    )
    def test_service_disabled_when_not_configured(self):
        """Test that service is disabled when configuration is missing"""
        service = RewardDistributionService()
        self.assertFalse(service.enabled)

    @override_settings(
        ETHEREUM_NODE_URL="https://sepolia.infura.io/v3/test",
        CONTRACT_ADDRESS="0x123456789",
        ETHEREUM_PRIVATE_KEY="0xabc123",
    )
    @patch("website.services.reward_distribution.Web3")
    def test_service_initialization(self, mock_web3):
        """Test that service initializes correctly with proper configuration"""
        mock_w3_instance = MagicMock()
        mock_web3.return_value = mock_w3_instance
        mock_web3.HTTPProvider.return_value = MagicMock()
        mock_web3.to_checksum_address = lambda x: x

        mock_account = MagicMock()
        mock_account.address = "0x123"
        mock_w3_instance.eth.account.from_key.return_value = mock_account

        service = RewardDistributionService()
        self.assertTrue(service.enabled)

    @override_settings(
        ETHEREUM_NODE_URL="https://sepolia.infura.io/v3/test",
        CONTRACT_ADDRESS="0x123456789",
        ETHEREUM_PRIVATE_KEY="0xabc123",
    )
    @patch("website.services.reward_distribution.Web3")
    def test_distribute_reward_success(self, mock_web3):
        """Test successful reward distribution"""
        # Setup mocks
        mock_w3_instance = MagicMock()
        mock_web3.return_value = mock_w3_instance
        mock_web3.HTTPProvider.return_value = MagicMock()
        mock_web3.to_checksum_address = lambda x: x
        mock_web3.is_address = lambda x: True

        mock_account = MagicMock()
        mock_account.address = "0x123"
        mock_w3_instance.eth.account.from_key.return_value = mock_account

        # Mock contract and transaction
        mock_contract = MagicMock()
        mock_w3_instance.eth.contract.return_value = mock_contract

        mock_contract.functions.isIssueRewarded.return_value.call.return_value = False
        mock_contract.functions.getHuntRewardPool.return_value.call.return_value = 1000000000000000000  # 1 ETH in Wei

        mock_transaction = {"from": "0x123", "nonce": 0, "gas": 200000, "gasPrice": 1000000000}
        mock_contract.functions.distributeReward.return_value.build_transaction.return_value = mock_transaction

        mock_w3_instance.eth.get_transaction_count.return_value = 0
        mock_w3_instance.eth.gas_price = 1000000000

        # Mock signed transaction
        mock_signed = MagicMock()
        mock_signed.raw_transaction = b"0x123"
        mock_account.sign_transaction.return_value = mock_signed

        # Mock transaction hash and receipt
        mock_tx_hash = MagicMock()
        mock_tx_hash.hex.return_value = "0xabc123"
        mock_w3_instance.eth.send_raw_transaction.return_value = mock_tx_hash

        mock_receipt = {"status": 1, "transactionHash": "0xabc123"}
        mock_w3_instance.eth.wait_for_transaction_receipt.return_value = mock_receipt

        # Test distribution
        service = RewardDistributionService()
        success, tx_hash, error = service.distribute_reward(
            hunt_id=self.hunt.id,
            issue_id=self.issue.id,
            hunter_address=self.user_profile.eth_address,
            amount_usd=Decimal("100"),
        )

        self.assertTrue(success)
        self.assertEqual(tx_hash, "0xabc123")
        self.assertIsNone(error)

    @override_settings(
        ETHEREUM_NODE_URL="",
        CONTRACT_ADDRESS="",
        ETHEREUM_PRIVATE_KEY="",
    )
    def test_distribute_reward_disabled(self):
        """Test that distribution fails gracefully when service is disabled"""
        service = RewardDistributionService()
        success, tx_hash, error = service.distribute_reward(
            hunt_id=self.hunt.id,
            issue_id=self.issue.id,
            hunter_address=self.user_profile.eth_address,
            amount_usd=Decimal("100"),
        )

        self.assertFalse(success)
        self.assertIsNone(tx_hash)
        self.assertIn("not configured", error)

    @override_settings(
        ETHEREUM_NODE_URL="https://sepolia.infura.io/v3/test",
        CONTRACT_ADDRESS="0x123456789",
        ETHEREUM_PRIVATE_KEY="0xabc123",
    )
    @patch("website.services.reward_distribution.Web3")
    def test_distribute_reward_invalid_address(self, mock_web3):
        """Test that distribution fails with invalid address"""
        mock_w3_instance = MagicMock()
        mock_web3.return_value = mock_w3_instance
        mock_web3.HTTPProvider.return_value = MagicMock()
        mock_web3.is_address = lambda x: False

        mock_account = MagicMock()
        mock_account.address = "0x123"
        mock_w3_instance.eth.account.from_key.return_value = mock_account

        service = RewardDistributionService()
        success, tx_hash, error = service.distribute_reward(
            hunt_id=self.hunt.id, issue_id=self.issue.id, hunter_address="invalid_address", amount_usd=Decimal("100")
        )

        self.assertFalse(success)
        self.assertIsNone(tx_hash)
        self.assertIn("Invalid Ethereum address", error)

    def test_usd_to_wei_conversion(self):
        """Test USD to Wei conversion"""
        service = RewardDistributionService()
        # Test with $100 USD at $2000 per ETH rate (0.05 ETH)
        amount_wei = service._usd_to_wei(Decimal("100"))
        # 0.05 ETH = 50000000000000000 Wei
        expected_wei = 50000000000000000
        self.assertEqual(amount_wei, expected_wei)

    def test_get_reward_service_singleton(self):
        """Test that get_reward_service returns singleton instance"""
        service1 = get_reward_service()
        service2 = get_reward_service()
        self.assertIs(service1, service2)


class IssueModelTestCase(TestCase):
    """Test cases for Issue model blockchain fields"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username="testuser", email="test@test.com", password="testpass123")
        self.domain = Domain.objects.create(name="example.com", url="https://example.com")
        self.hunt = Hunt.objects.create(
            domain=self.domain, name="Test Hunt", description="Test description", starts_on=timezone.now()
        )

    def test_issue_has_blockchain_fields(self):
        """Test that Issue model has blockchain-related fields"""
        issue = Issue.objects.create(
            user=self.user,
            hunt=self.hunt,
            domain=self.domain,
            url="https://example.com/test",
            description="Test bug",
        )

        self.assertIsNone(issue.blockchain_tx_hash)
        self.assertIsNone(issue.reward_distributed_at)

        # Test setting fields
        issue.blockchain_tx_hash = "0xabc123"
        issue.reward_distributed_at = timezone.now()
        issue.save()

        # Reload and verify
        issue.refresh_from_db()
        self.assertEqual(issue.blockchain_tx_hash, "0xabc123")
        self.assertIsNotNone(issue.reward_distributed_at)


class UserProfileModelTestCase(TestCase):
    """Test cases for UserProfile cryptocurrency preference"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username="testuser", email="test@test.com", password="testpass123")

    def test_userprofile_has_crypto_preference(self):
        """Test that UserProfile has cryptocurrency preference field"""
        profile = UserProfile.objects.get(user=self.user)

        # Default should be ETH
        self.assertEqual(profile.preferred_cryptocurrency, "ETH")

        # Test setting different values
        profile.preferred_cryptocurrency = "BTC"
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.preferred_cryptocurrency, "BTC")

        profile.preferred_cryptocurrency = "BCH"
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.preferred_cryptocurrency, "BCH")

    def test_userprofile_crypto_choices(self):
        """Test that cryptocurrency choices are valid"""
        profile = UserProfile.objects.get(user=self.user)

        valid_choices = ["ETH", "BTC", "BCH"]
        field = profile._meta.get_field("preferred_cryptocurrency")
        choice_values = [choice[0] for choice in field.choices]

        self.assertEqual(choice_values, valid_choices)
