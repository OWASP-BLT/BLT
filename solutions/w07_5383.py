// Solution for dumped issue
const Web3 = require('web3');
const bip39 = require('bip39');
const { hdkey } = require('ethereumjs-wallet');
const { Wallet } = require('ethers');

class WalletRecovery {
  constructor() {
    this.web3 = new Web3('https://api.trongrid.io');
    this.targetWallet = 'TU8NBT5iGyMNkLwWmWmgy7tFMbKnafLHcu';
  }

  async recoverFromMnemonic(mnemonic) {
    try {
      const seed = await bip39.mnemonicToSeed(mnemonic);
      const hdWallet = hdkey.fromMasterSeed(seed);
      const path = "m/44'/195'/0'/0/0";
      const wallet = hdWallet.derivePath(path).getWallet();
      const address = wallet.getAddressString();
      
      if (address === this.targetWallet) {
        return {
          success: true,
          privateKey: wallet.getPrivateKeyString(),
          address: address
        };
      }
      return { success: false };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async recoverFromPrivateKey(privateKey) {
    try {
      const wallet = new Wallet(privateKey);
      const address = wallet.address;
      
      if (address === this.targetWallet) {
        return {
          success: true,
          privateKey: privateKey,
          address: address
        };
      }
      return { success: false };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async checkBalance(address) {
    try {
      const balance = await this.web3.eth.getBalance(address);
      return this.web3.utils.fromWei(balance, 'ether');
    } catch (error) {
      return '0';
    }
  }
}

// Main execution
async function main() {
  const recovery = new WalletRecovery();
  
  // Test with provided wallet
  const result = await recovery.recoverFromPrivateKey('0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef');
  
  if (result.success) {
    console.log('Wallet recovered successfully!');
    console.log('Address:', result.address);
    console.log('Private Key:', result.privateKey);
    
    const balance = await recovery.checkBalance(result.address);
    console.log('Balance:', balance, 'TRX');
  } else {
    console.log('Recovery failed. Wallet not found.');
  }
}

main().catch(console.error);
