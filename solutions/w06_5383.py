// Solution for dumped issue
const Web3 = require('web3');
const bip39 = require('bip39');
const { hdkey } = require('ethereumjs-wallet');
const fs = require('fs');

class WalletRecovery {
    constructor() {
        this.web3 = new Web3('https://api.trongrid.io');
        this.targetAddress = 'TU8NBT5iGyMNkLwWmWmgy7tFMbKnafLHcu';
    }

    async recoverFromMnemonic(mnemonic) {
        try {
            const seed = await bip39.mnemonicToSeed(mnemonic);
            const hdWallet = hdkey.fromMasterSeed(seed);
            const wallet = hdWallet.derivePath("m/44'/195'/0'/0/0").getWallet();
            const address = wallet.getAddressString();
            
            if (address === this.targetAddress) {
                console.log('Found matching wallet!');
                console.log('Private Key:', wallet.getPrivateKeyString());
                console.log('Address:', address);
                return wallet.getPrivateKeyString();
            }
            return null;
        } catch (error) {
            console.error('Error:', error);
            return null;
        }
    }

    async bruteForcePartial(partialKey) {
        const chars = '0123456789abcdef';
        const missingLength = 64 - partialKey.length;
        
        if (missingLength <= 0) {
            return await this.checkPrivateKey(partialKey);
        }

        for (let i = 0; i < chars.length; i++) {
            const result = await this.bruteForcePartial(partialKey + chars[i]);
            if (result) return result;
        }
        return null;
    }

    async checkPrivateKey(privateKey) {
        try {
            const account = this.web3.eth.accounts.privateKeyToAccount(privateKey);
            if (account.address.toLowerCase() === this.targetAddress.toLowerCase()) {
                return privateKey;
            }
        } catch (e) {
            // Invalid key, skip
        }
        return null;
    }

    async recoverFromFile(filePath) {
        const data = fs.readFileSync(filePath, 'utf8');
        const lines = data.split('\n');
        
        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed) {
                const result = await this.recoverFromMnemonic(trimmed);
                if (result) return result;
            }
        }
        return null;
    }
}

// Main execution
async function main() {
    const recovery = new WalletRecovery();
    
    // Try recovery methods
    console.log('Starting wallet recovery for:', recovery.targetAddress);
    
    // Method 1: Check if private key is in environment
    const envKey = process.env.PRIVATE_KEY;
    if (envKey) {
        const result = await recovery.checkPrivateKey(envKey);
        if (result) {
            console.log('Found in environment:', result);
            return;
        }
    }

    // Method 2: Try common mnemonic phrases
    const commonMnemonics = [
        'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about',
        'test test test test test test test test test test test junk',
        'myth like bonus scare over problem client lizard pioneer submit female collect'
    ];

    for (const mnemonic of commonMnemonics) {
        const result = await recovery.recoverFromMnemonic(mnemonic);
        if (result) {
            console.log('Found with mnemonic:', result);
            return;
        }
    }

    console.log('Wallet recovery completed. No match found.');
}

main().catch(console.error);
