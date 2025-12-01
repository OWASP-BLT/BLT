# Bug Bounty Reward Smart Contract

This directory contains the Solidity smart contract for automatic distribution of bug bounty rewards on the Ethereum blockchain.

## Overview

The `BugBountyReward` smart contract enables:
- Automatic distribution of bug bounty rewards to hunters
- Multi-hunt management with separate reward pools
- Transparent on-chain tracking of all reward distributions
- Secure fund management for organizations

## Smart Contract: BugBountyReward.sol

### Key Features

1. **Hunt Management**: Organizations can create bug hunts with dedicated reward pools
2. **Automatic Distribution**: Rewards are automatically distributed when bugs are approved
3. **Transparency**: All distributions are recorded on-chain and emit events
4. **Security**: Only authorized addresses can distribute rewards
5. **Fund Recovery**: Organizations can withdraw unused funds

### Main Functions

#### For Contract Owner (BLT Platform)

- `createHunt(uint256 _huntId, address _organization)`: Create a new bug hunt
- `distributeReward(uint256 _huntId, uint256 _issueId, address _hunter, uint256 _amount)`: Distribute reward to hunter
- `deactivateHunt(uint256 _huntId)`: Deactivate a hunt
- `transferOwnership(address _newOwner)`: Transfer contract ownership

#### For Organizations

- `fundHunt(uint256 _huntId)`: Add funds to a hunt's reward pool (payable)
- `withdrawFunds(uint256 _huntId, uint256 _amount)`: Withdraw unused funds

#### View Functions

- `getHuntRewardPool(uint256 _huntId)`: Get current reward pool balance for a hunt
- `isIssueRewarded(uint256 _huntId, uint256 _issueId)`: Check if an issue was already rewarded
- `getHuntRewards(uint256 _huntId)`: Get all reward distributions for a hunt

### Events

- `HuntCreated`: Emitted when a new hunt is created
- `RewardPoolFunded`: Emitted when a hunt is funded
- `RewardDistributed`: Emitted when a reward is distributed to a hunter
- `FundsWithdrawn`: Emitted when an organization withdraws funds

## Deployment

### Prerequisites

1. Install Solidity compiler (solc):
   ```bash
   npm install -g solc
   ```

2. Install web3.py (already in requirements):
   ```bash
   pip install web3
   ```

3. Set up environment variables in `.env`:
   ```
   ETHEREUM_NODE_URL=https://mainnet.infura.io/v3/YOUR_INFURA_KEY
   ETHEREUM_PRIVATE_KEY=your_private_key
   CONTRACT_ADDRESS=deployed_contract_address
   ```

### Deployment Steps

1. Compile the contract:
   ```bash
   solc --bin --abi contracts/BugBountyReward.sol -o contracts/build/
   ```

2. Deploy using the Django management command:
   ```bash
   python manage.py deploy_reward_contract
   ```

3. The deployment will output the contract address - save this in your environment variables.

### Testing on Testnet

Before deploying to mainnet, test on a testnet (e.g., Sepolia, Goerli):

1. Get testnet ETH from a faucet
2. Update `ETHEREUM_NODE_URL` to point to testnet
3. Deploy and test all functions
4. Verify reward distribution works as expected

## Integration with BLT

The smart contract integrates with the BLT platform through:

1. **Reward Distribution Service** (`website/services/reward_distribution.py`)
   - Handles Web3 interactions
   - Manages transaction signing and submission
   - Handles errors and retries

2. **Modified Accept Bug Flow** (`website/views/company.py`)
   - When a bug is approved, triggers smart contract reward distribution
   - Falls back to manual distribution if blockchain transaction fails

3. **User Cryptocurrency Preferences**
   - Users can specify their preferred cryptocurrency wallet
   - System converts between fiat and cryptocurrency amounts

## Security Considerations

1. **Private Key Management**: Never commit private keys to version control
2. **Access Control**: Only the contract owner (BLT platform) can distribute rewards
3. **Reentrancy Protection**: Uses checks-effects-interactions pattern
4. **Emergency Functions**: Emergency withdrawal available for owner
5. **Testing**: Thoroughly test on testnet before mainnet deployment

## Gas Optimization

The contract is optimized for gas efficiency:
- Uses `uint256` for IDs and amounts
- Minimal storage operations
- Efficient event emissions
- Batch operations where possible

## Future Enhancements

Potential improvements for future versions:
- Support for ERC-20 token rewards (USDC, DAI, etc.)
- Multi-signature approval for large rewards
- Scheduled/delayed reward distribution
- Integration with Layer 2 solutions for lower gas fees
- Support for other blockchain networks (Polygon, BSC, etc.)

## Support

For questions or issues related to the smart contract:
- Create an issue on the BLT GitHub repository
- Contact the development team
- Review the contract code and tests

## License

This smart contract is licensed under AGPL-3.0, same as the BLT project.
