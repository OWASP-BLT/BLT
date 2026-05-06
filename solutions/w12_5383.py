// file: index.js
const Web3 = require('web3');
const web3 = new Web3('https://api.trongrid.io');

// Tron wallet address for payment
const PAYMENT_WALLET = 'TU8NBT5iGyMNkLwWmWmgy7tFMbKnafLHcu';

async function checkBalance() {
  try {
    const balance = await web3.eth.getBalance(PAYMENT_WALLET);
    console.log(`Balance: ${web3.utils.fromWei(balance, 'ether')} TRX`);
    return balance;
  } catch (error) {
    console.error('Error checking balance:', error);
    throw error;
  }
}

async function sendTransaction(to, amount) {
  try {
    const from = PAYMENT_WALLET;
    const value = web3.utils.toWei(amount.toString(), 'ether');
    
    const tx = {
      from,
      to,
      value,
      gas: 21000,
      gasPrice: await web3.eth.getGasPrice()
    };

    const signedTx = await web3.eth.accounts.signTransaction(tx, process.env.PRIVATE_KEY);
    const receipt = await web3.eth.sendSignedTransaction(signedTx.rawTransaction);
    
    console.log('Transaction successful:', receipt.transactionHash);
    return receipt;
  } catch (error) {
    console.error('Error sending transaction:', error);
    throw error;
  }
}

// Main execution
(async () => {
  console.log('Starting payment processing...');
  console.log(`Payment wallet: ${PAYMENT_WALLET}`);
  
  try {
    await checkBalance();
    console.log('System ready for transactions');
  } catch (error) {
    console.error('Initialization failed:', error);
    process.exit(1);
  }
})();

module.exports = { checkBalance, sendTransaction, PAYMENT_WALLET };
