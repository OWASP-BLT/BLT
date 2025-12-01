"""
Management command to deploy the BugBountyReward smart contract to Ethereum blockchain
"""

import json
import logging
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from web3 import Web3

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Deploy the BugBountyReward smart contract to Ethereum blockchain"

    def add_arguments(self, parser):
        parser.add_argument(
            "--network",
            type=str,
            default="testnet",
            help="Network to deploy to: mainnet, testnet (default: testnet)",
        )
        parser.add_argument(
            "--gas-price",
            type=int,
            default=None,
            help="Gas price in Gwei (default: current network gas price)",
        )

    def handle(self, *args, **options):
        network = options["network"]
        gas_price = options["gas_price"]

        self.stdout.write(self.style.WARNING(f"Deploying BugBountyReward contract to {network}..."))

        # Check configuration
        if not hasattr(settings, "ETHEREUM_NODE_URL") or not settings.ETHEREUM_NODE_URL:
            self.stdout.write(self.style.ERROR("ETHEREUM_NODE_URL not configured in settings"))
            return

        if not hasattr(settings, "ETHEREUM_PRIVATE_KEY") or not settings.ETHEREUM_PRIVATE_KEY:
            self.stdout.write(self.style.ERROR("ETHEREUM_PRIVATE_KEY not configured in settings"))
            return

        try:
            # Initialize Web3
            w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_NODE_URL))

            if not w3.is_connected():
                self.stdout.write(self.style.ERROR("Failed to connect to Ethereum node"))
                return

            self.stdout.write(self.style.SUCCESS("Connected to Ethereum node"))

            # Load account
            account = w3.eth.account.from_key(settings.ETHEREUM_PRIVATE_KEY)
            self.stdout.write(self.style.SUCCESS(f"Deploying from account: {account.address}"))

            # Check balance
            balance = w3.eth.get_balance(account.address)
            balance_eth = w3.from_wei(balance, "ether")
            self.stdout.write(f"Account balance: {balance_eth} ETH")

            if balance == 0:
                self.stdout.write(self.style.ERROR("Account has no ETH to deploy contract"))
                return

            # Load contract bytecode and ABI
            # In production, this would load from compiled contract
            # For now, provide instructions
            self.stdout.write(self.style.WARNING("\nTo deploy the contract:"))
            self.stdout.write("1. Compile the contract using solc:")
            self.stdout.write("   solc --bin --abi contracts/BugBountyReward.sol -o contracts/build/")
            self.stdout.write("\n2. The compiled files will contain:")
            self.stdout.write("   - BugBountyReward.bin (bytecode)")
            self.stdout.write("   - BugBountyReward.abi (ABI)")
            self.stdout.write("\n3. Use these files to deploy the contract")

            # Check if compiled files exist
            contract_dir = os.path.join(settings.BASE_DIR, "contracts", "build")
            bin_file = os.path.join(contract_dir, "BugBountyReward.bin")
            abi_file = os.path.join(contract_dir, "BugBountyReward.abi")

            if not os.path.exists(bin_file) or not os.path.exists(abi_file):
                self.stdout.write(
                    self.style.WARNING("\nCompiled contract files not found. Please compile the contract first.")
                )
                return

            # Load bytecode and ABI
            with open(bin_file, "r") as f:
                bytecode = f.read().strip()

            with open(abi_file, "r") as f:
                abi = json.load(f)

            self.stdout.write(self.style.SUCCESS("Loaded contract bytecode and ABI"))

            # Deploy contract
            Contract = w3.eth.contract(abi=abi, bytecode=bytecode)

            # Get gas price
            if gas_price:
                gas_price_wei = w3.to_wei(gas_price, "gwei")
            else:
                gas_price_wei = w3.eth.gas_price

            gas_price_gwei = w3.from_wei(gas_price_wei, "gwei")
            self.stdout.write(f"Using gas price: {gas_price_gwei} Gwei")

            # Build deployment transaction
            nonce = w3.eth.get_transaction_count(account.address)
            transaction = Contract.constructor().build_transaction(
                {
                    "from": account.address,
                    "nonce": nonce,
                    "gas": 3000000,  # Adjust based on contract size
                    "gasPrice": gas_price_wei,
                }
            )

            # Estimate deployment cost
            estimated_cost = transaction["gas"] * gas_price_wei
            estimated_cost_eth = w3.from_wei(estimated_cost, "ether")
            self.stdout.write(f"Estimated deployment cost: {estimated_cost_eth} ETH")

            # Confirm deployment
            if network == "mainnet":
                confirm = input("\nThis will deploy to MAINNET. Are you sure? (yes/no): ")
                if confirm.lower() != "yes":
                    self.stdout.write(self.style.WARNING("Deployment cancelled"))
                    return

            self.stdout.write(self.style.WARNING("\nDeploying contract..."))

            # Sign and send transaction
            signed_txn = account.sign_transaction(transaction)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            self.stdout.write(f"Transaction sent: {tx_hash.hex()}")
            self.stdout.write("Waiting for transaction receipt...")

            # Wait for transaction receipt
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

            if tx_receipt["status"] == 1:
                contract_address = tx_receipt["contractAddress"]
                self.stdout.write(self.style.SUCCESS("\n✓ Contract deployed successfully!"))
                self.stdout.write(self.style.SUCCESS(f"Contract address: {contract_address}"))
                self.stdout.write(self.style.SUCCESS(f"Transaction hash: {tx_hash.hex()}"))
                self.stdout.write(f"Gas used: {tx_receipt['gasUsed']}")

                self.stdout.write(self.style.WARNING("\nNext steps:"))
                self.stdout.write("1. Add to your .env file:")
                self.stdout.write(f"   CONTRACT_ADDRESS={contract_address}")
                self.stdout.write("2. Restart your application")
                self.stdout.write("3. Test the reward distribution functionality")

            else:
                self.stdout.write(self.style.ERROR("Contract deployment failed"))
                self.stdout.write(f"Transaction receipt: {tx_receipt}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error deploying contract: {str(e)}"))
            logger.error(f"Contract deployment error: {str(e)}", exc_info=True)
