# Automatic Reward Distribution System

## Overview

The BLT platform now supports automatic distribution of bug bounty rewards using Ethereum smart contracts. When a bug submission is approved, the system can automatically transfer the reward to the bug hunter's cryptocurrency wallet.

## Features

- **Automatic Distribution**: Rewards are automatically distributed when bugs are approved
- **Smart Contract Based**: Uses Ethereum blockchain for transparent, immutable transactions
- **Multi-Cryptocurrency Support**: Users can choose their preferred cryptocurrency (ETH, BTC, BCH)
- **Fallback Mechanism**: Falls back to manual distribution if automatic fails
- **Transaction Tracking**: All distributions are recorded on-chain with transaction hashes
- **Security**: Only authorized platform account can distribute rewards

## Architecture

### Components

1. **Smart Contract** (`contracts/BugBountyReward.sol`)
   - Solidity smart contract deployed on Ethereum
   - Manages reward pools for different hunts
   - Handles automatic distribution logic
   - Prevents double-spending and ensures transparency

2. **Reward Distribution Service** (`website/services/reward_distribution.py`)
   - Python service layer using web3.py
   - Interfaces with the smart contract
   - Handles transaction signing and submission
   - Manages errors and retries

3. **Database Models** (Updates to `website/models.py`)
   - `Issue.blockchain_tx_hash`: Stores transaction hash for distributed rewards
   - `Issue.reward_distributed_at`: Timestamp of distribution
   - `UserProfile.preferred_cryptocurrency`: User's preferred crypto for rewards

4. **Integration** (`website/views/company.py`)
   - Modified `accept_bug` function to trigger automatic distribution
   - Provides user feedback on distribution status
   - Falls back gracefully if automatic distribution fails

## Setup Instructions

### Prerequisites

1. **Ethereum Node Access**: You need access to an Ethereum node (Infura, Alchemy, or self-hosted)
2. **Wallet with ETH**: An Ethereum wallet with sufficient ETH for gas fees and rewards
3. **Solidity Compiler**: For compiling the smart contract

### Step 1: Install Dependencies

The required dependencies are already added to `pyproject.toml`:

```bash
# If using poetry (recommended)
poetry install

# Or if using pip
pip install web3
```

### Step 2: Compile the Smart Contract

```bash
# Install Solidity compiler if not already installed
npm install -g solc

# Compile the contract
solc --bin --abi contracts/BugBountyReward.sol -o contracts/build/
```

This will generate:
- `contracts/build/BugBountyReward.bin` - Contract bytecode
- `contracts/build/BugBountyReward.abi` - Contract ABI

### Step 3: Deploy the Smart Contract

**Important**: Test on a testnet (Sepolia, Goerli) before deploying to mainnet!

```bash
# Set environment variables in .env
ETHEREUM_NODE_URL=https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID
ETHEREUM_PRIVATE_KEY=your_private_key_here

# Deploy using management command
python manage.py deploy_reward_contract --network testnet

# For mainnet (use with caution!)
python manage.py deploy_reward_contract --network mainnet
```

The command will output the deployed contract address. Save this!

### Step 4: Configure Environment Variables

Add to your `.env` file:

```bash
# Ethereum Configuration
ETHEREUM_NODE_URL=https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID
CONTRACT_ADDRESS=0x_your_deployed_contract_address
ETHEREUM_PRIVATE_KEY=your_private_key_here
```

**Security Note**: Never commit your private key to version control!

### Step 5: Run Database Migrations

```bash
python manage.py migrate
```

This will add the necessary fields to the database.

### Step 6: Test the System

1. Create a test hunt
2. Submit a test bug
3. Approve the bug with a reward
4. Verify the transaction on Etherscan (testnet)

## User Guide

### For Bug Hunters

1. **Set Your Crypto Wallet**:
   - Go to your profile settings
   - Add your Ethereum address (ETH)
   - Select your preferred cryptocurrency
   - Save your profile

2. **Submit Bugs**:
   - Submit bugs as usual through the platform
   - When approved, rewards will be automatically sent to your wallet

3. **Track Your Rewards**:
   - View your issues to see transaction hashes
   - Verify transactions on Etherscan
   - Check your wallet for received funds

### For Organization Admins

1. **Fund Your Hunt**:
   - Deploy your hunt as usual
   - Optionally fund the smart contract (future enhancement)
   - Platform will handle distributions automatically

2. **Approve Bugs**:
   - Review and approve bug submissions
   - System automatically distributes rewards
   - You'll see confirmation messages

3. **Monitor Distributions**:
   - Check issue details for transaction hashes
   - Verify on blockchain explorer
   - Track total distributed amounts

## Technical Details

### Smart Contract Functions

#### Public Functions

- `createHunt(uint256 _huntId, address _organization)`: Create a new hunt
- `fundHunt(uint256 _huntId)`: Add funds to hunt reward pool (payable)
- `distributeReward(uint256 _huntId, uint256 _issueId, address _hunter, uint256 _amount)`: Distribute reward
- `getHuntRewardPool(uint256 _huntId)`: Check reward pool balance
- `isIssueRewarded(uint256 _huntId, uint256 _issueId)`: Check if issue was rewarded
- `withdrawFunds(uint256 _huntId, uint256 _amount)`: Organization withdraws unused funds

#### Events

- `HuntCreated`: Emitted when hunt is created
- `RewardPoolFunded`: Emitted when hunt is funded
- `RewardDistributed`: Emitted when reward is sent
- `FundsWithdrawn`: Emitted when funds are withdrawn

### Reward Distribution Flow

1. **Bug Approval**:
   ```python
   accept_bug(request, issue_id, reward_id)
   ```

2. **Service Call**:
   ```python
   reward_service.distribute_reward(
       hunt_id, issue_id, hunter_address, amount_usd
   )
   ```

3. **Transaction Creation**:
   - Convert USD to Wei
   - Build transaction
   - Sign with platform's private key

4. **Transaction Submission**:
   - Send to Ethereum network
   - Wait for confirmation
   - Return transaction hash

5. **Database Update**:
   - Store transaction hash
   - Record distribution timestamp
   - Update issue status

### Gas Optimization

The smart contract is optimized for gas efficiency:
- Uses `uint256` for IDs and amounts
- Minimal storage operations
- Efficient mapping structures
- Single transaction per distribution

Average gas costs (approximate):
- Create Hunt: ~150,000 gas
- Distribute Reward: ~100,000-200,000 gas
- Fund Hunt: ~50,000 gas

### Error Handling

The system handles various error scenarios:

1. **Configuration Missing**: Service disabled, manual distribution required
2. **Invalid Address**: Error logged, manual distribution
3. **Insufficient Funds**: Error message, manual distribution
4. **Transaction Failure**: Retry logic, fallback to manual
5. **Network Issues**: Timeout handling, clear error messages

## Security Considerations

### Smart Contract Security

- **Access Control**: Only platform owner can distribute rewards
- **Reentrancy Protection**: Uses checks-effects-interactions pattern
- **Double Distribution Prevention**: Tracks rewarded issues
- **Emergency Functions**: Owner can emergency withdraw if needed

### Private Key Security

- Store private key in environment variables only
- Never commit to version control
- Use hardware wallets for mainnet
- Consider multi-signature for large amounts
- Rotate keys periodically

### Best Practices

1. **Test Thoroughly**: Always test on testnet first
2. **Monitor Gas Prices**: Distribute during low gas periods
3. **Verify Transactions**: Check on blockchain explorer
4. **Backup Keys**: Securely backup private keys
5. **Audit Contract**: Consider professional audit for mainnet

## Troubleshooting

### Common Issues

**Issue**: "Reward distribution service is not configured"
- **Solution**: Set ETHEREUM_NODE_URL, CONTRACT_ADDRESS, and ETHEREUM_PRIVATE_KEY in .env

**Issue**: "Invalid Ethereum address"
- **Solution**: Verify user's ETH address is valid and checksummed

**Issue**: "Insufficient reward pool"
- **Solution**: Fund the contract or use manual distribution

**Issue**: "Transaction failed"
- **Solution**: Check gas price, network congestion, and account balance

**Issue**: Contract deployment fails
- **Solution**: Ensure account has sufficient ETH for gas fees

### Logging

Check logs for detailed error messages:

```bash
# In Django
tail -f logs/django.log | grep reward

# Or check specific logger
python manage.py shell
>>> import logging
>>> logger = logging.getLogger('website.services.reward_distribution')
>>> logger.info('Test message')
```

## Future Enhancements

Potential improvements for future versions:

1. **Multi-Token Support**: Support for ERC-20 tokens (USDC, DAI)
2. **Layer 2 Integration**: Use Layer 2 solutions for lower gas fees
3. **Batch Distributions**: Distribute multiple rewards in one transaction
4. **Price Oracle**: Real-time ETH/USD conversion using Chainlink
5. **Multi-Signature**: Require multiple approvals for large rewards
6. **Scheduled Distributions**: Delay rewards for dispute period
7. **Cross-Chain**: Support for multiple blockchains (Polygon, BSC)

## Support and Contribution

- **Issues**: Report bugs on GitHub Issues
- **Contributions**: Submit PRs with improvements
- **Documentation**: Help improve this documentation
- **Testing**: Test on various networks and scenarios

## License

This reward distribution system is part of the BLT project and is licensed under AGPL-3.0.

## References

- [Web3.py Documentation](https://web3py.readthedocs.io/)
- [Solidity Documentation](https://docs.soliditylang.org/)
- [Ethereum Development](https://ethereum.org/en/developers/)
- [Infura Documentation](https://docs.infura.io/)
- [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts/)
