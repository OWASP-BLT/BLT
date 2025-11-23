# Quick Start: Automatic Reward Distribution

This guide will help you quickly set up and test the automatic reward distribution system.

## Overview

The system automatically sends cryptocurrency rewards to bug hunters when their submissions are approved. It uses Ethereum smart contracts for transparency and automation.

## Quick Setup (5 minutes)

### 1. Get an Ethereum Node URL

Sign up for a free account at [Infura](https://infura.io/) or [Alchemy](https://www.alchemy.com/):

- Infura: https://infura.io/register
- Alchemy: https://www.alchemy.com/

Create a new project and copy your API endpoint URL.

### 2. Create a Test Wallet

**For Testing Only** - Use a testnet wallet:

```bash
# Using Python
python -c "from web3 import Web3; w3 = Web3(); acc = w3.eth.account.create(); print(f'Address: {acc.address}\nPrivate Key: {acc.key.hex()}')"
```

**Important**: Never use a wallet with real funds for testing!

### 3. Get Test ETH

For Sepolia testnet:
- Visit https://sepoliafaucet.com/
- Enter your wallet address
- Request test ETH

### 4. Configure Environment

Add to your `.env` file:

```bash
# Use Sepolia testnet for testing
ETHEREUM_NODE_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
ETHEREUM_PRIVATE_KEY=0xyour_test_wallet_private_key
CONTRACT_ADDRESS=  # Leave empty for now, will be filled after deployment
```

### 5. Install Dependencies

```bash
# If using poetry (recommended)
poetry install

# If using pip
pip install web3
```

### 6. Compile and Deploy Contract

```bash
# Install Solidity compiler (one-time setup)
npm install -g solc

# Compile the contract
mkdir -p contracts/build
solc --bin --abi contracts/BugBountyReward.sol -o contracts/build/

# Deploy to testnet
python manage.py deploy_reward_contract --network testnet
```

Copy the deployed contract address and add it to your `.env`:

```bash
CONTRACT_ADDRESS=0x_your_deployed_contract_address
```

### 7. Restart Your Application

```bash
# Restart Django
python manage.py runserver
```

## Testing the System

### Step 1: Configure a Test User

1. Create or login as a bug hunter
2. Go to Profile Settings
3. Add your test Ethereum address:
   - Create a new test wallet address (different from the platform wallet)
   - Add it to the "ETH Address" field
4. Select "Ethereum (ETH)" as preferred cryptocurrency
5. Save profile

### Step 2: Create a Test Hunt

1. Create an organization (or use existing)
2. Create a new bug hunt
3. Add a reward tier (e.g., $100)

### Step 3: Submit and Approve a Bug

1. Submit a test bug to the hunt
2. As an admin, approve the bug with the reward
3. Watch for automatic distribution!

### Step 4: Verify the Transaction

1. Check the issue page - it should show a transaction hash
2. Visit Sepolia Etherscan: https://sepolia.etherscan.io/
3. Search for your transaction hash
4. Verify the reward was sent

## Expected Behavior

### ✅ Successful Distribution

- User sees: "Bug accepted and reward automatically distributed! Transaction: 0xabc123..."
- Issue shows transaction hash and timestamp
- Transaction visible on Etherscan
- Hunter's wallet receives ETH

### ⚠️ Fallback to Manual

If automatic distribution fails:
- User sees: "Bug accepted. Automatic reward distribution failed - please distribute manually."
- Issue is still approved
- Admin can distribute reward manually

## Common Issues

### "Reward distribution service is not configured"

**Solution**: Check your `.env` file has all three variables set:
```bash
ETHEREUM_NODE_URL=...
ETHEREUM_PRIVATE_KEY=...
CONTRACT_ADDRESS=...
```

### "Insufficient funds for gas"

**Solution**: Your platform wallet needs testnet ETH for gas fees:
- Visit https://sepoliafaucet.com/
- Request test ETH for your platform wallet address

### "No crypto address configured for user"

**Solution**: The bug hunter needs to:
1. Go to their profile settings
2. Add an Ethereum address
3. Save their profile

### Contract deployment fails

**Solution**: 
- Ensure wallet has testnet ETH
- Check Solidity compiler is installed: `solc --version`
- Verify contract compiles: `solc contracts/BugBountyReward.sol`

## Production Deployment

**⚠️ Important**: Before deploying to mainnet:

1. **Security Audit**: Have the smart contract professionally audited
2. **Thorough Testing**: Test extensively on testnet
3. **Secure Keys**: Use hardware wallet or HSM for private keys
4. **Gas Budget**: Ensure sufficient ETH for gas fees
5. **Monitoring**: Set up alerts for transactions
6. **Backup Plan**: Have manual distribution process ready

### Mainnet Checklist

- [ ] Smart contract audited
- [ ] Tested on testnet for at least 2 weeks
- [ ] Secure key management in place
- [ ] Monitoring and alerts configured
- [ ] Documentation reviewed
- [ ] Team trained on the system
- [ ] Backup procedures documented
- [ ] Insurance/risk assessment completed

### Deploy to Mainnet

```bash
# Update .env with mainnet node URL
ETHEREUM_NODE_URL=https://mainnet.infura.io/v3/YOUR_PROJECT_ID

# Deploy (requires confirmation)
python manage.py deploy_reward_contract --network mainnet
```

## Support

- **Documentation**: See `docs/REWARD_DISTRIBUTION.md` for detailed information
- **Smart Contract**: See `contracts/README.md` for contract details
- **Issues**: Report problems on GitHub Issues
- **Security**: Report security issues privately to the maintainers

## Features Overview

| Feature | Status | Notes |
|---------|--------|-------|
| Ethereum (ETH) Distribution | ✅ Implemented | Fully functional |
| Bitcoin (BTC) Distribution | 🔄 Planned | Requires wrapped BTC or different implementation |
| Bitcoin Cash (BCH) Distribution | 🔄 Planned | Existing BCH system can be integrated |
| Transaction Tracking | ✅ Implemented | On-chain verification |
| Multi-signature | 🔄 Planned | For large rewards |
| Batch Distribution | 🔄 Planned | Gas optimization |
| Price Oracle | 🔄 Planned | Real-time USD/ETH conversion |

## Cost Estimation

### Testnet
- **Cost**: Free (using test ETH)
- **Purpose**: Testing and development
- **Recommendation**: Use for all initial testing

### Mainnet
- **Deployment**: ~$30-100 (depending on gas prices)
- **Per Distribution**: ~$5-50 per transaction (varies with gas prices)
- **Optimization**: Deploy during low gas periods (weekends, non-US hours)

## Tips for Success

1. **Start Small**: Test with small amounts first
2. **Monitor Gas**: Track gas prices and distribute during low periods
3. **User Education**: Teach users how to set up crypto wallets
4. **Clear Communication**: Inform users about distribution status
5. **Have Backup**: Always have manual distribution as fallback
6. **Document Everything**: Keep records of all distributions
7. **Security First**: Never compromise on security practices

## Next Steps

After successful testing:

1. ✅ Document your testing process
2. ✅ Train team members on the system
3. ✅ Set up monitoring and alerts
4. ✅ Create user guides for bug hunters
5. ✅ Plan for mainnet deployment
6. ✅ Consider professional security audit

---

**Need Help?** Check the full documentation in `docs/REWARD_DISTRIBUTION.md` or open an issue on GitHub.
