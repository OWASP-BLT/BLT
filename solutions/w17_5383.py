// File: p2p-blockchain-sync.js
// Solves issue: "dumped" - implements a robust P2P blockchain synchronization mechanism

const crypto = require('crypto');
const EventEmitter = require('events');

class Block {
  constructor(index, previousHash, timestamp, data, hash, nonce = 0) {
    this.index = index;
    this.previousHash = previousHash;
    this.timestamp = timestamp;
    this.data = data;
    this.hash = hash;
    this.nonce = nonce;
  }

  static calculateHash(index, previousHash, timestamp, data, nonce) {
    return crypto
      .createHash('sha256')
      .update(index + previousHash + timestamp + JSON.stringify(data) + nonce)
      .digest('hex');
  }

  static isValidBlock(newBlock, previousBlock) {
    if (previousBlock.index + 1 !== newBlock.index) {
      return false;
    }
    if (previousBlock.hash !== newBlock.previousHash) {
      return false;
    }
    const calculatedHash = Block.calculateHash(
      newBlock.index,
      newBlock.previousHash,
      newBlock.timestamp,
      newBlock.data,
      newBlock.nonce
    );
    if (calculatedHash !== newBlock.hash) {
      return false;
    }
    return true;
  }
}

class P2PNode extends EventEmitter {
  constructor(port, peers = []) {
    super();
    this.port = port;
    this.peers = peers;
    this.blockchain = [];
    this.pendingTransactions = [];
    this.difficulty = 4;
    this.miningReward = 10;
    this.isMining = false;

    // Initialize with genesis block
    this.createGenesisBlock();
  }

  createGenesisBlock() {
    const genesisBlock = new Block(
      0,
      '0',
      Date.now(),
      { transactions: [], message: 'Genesis Block' },
      '0'
    );
    genesisBlock.hash = Block.calculateHash(
      genesisBlock.index,
      genesisBlock.previousHash,
      genesisBlock.timestamp,
      genesisBlock.data,
      genesisBlock.nonce
    );
    this.blockchain.push(genesisBlock);
  }

  getLatestBlock() {
    return this.blockchain[this.blockchain.length - 1];
  }

  addTransaction(transaction) {
    if (!transaction.from || !transaction.to) {
      throw new Error('Transaction must include from and to addresses');
    }
    this.pendingTransactions.push(transaction);
    this.broadcastTransaction(transaction);
  }

  minePendingTransactions(miningRewardAddress) {
    if (this.isMining) {
      console.log('Already mining...');
      return;
    }

    this.isMining = true;
    const rewardTransaction = {
      from: null,
      to: miningRewardAddress,
      amount: this.miningReward,
      timestamp: Date.now()
    };
    this.pendingTransactions.push(rewardTransaction);

    const block = new Block(
      this.blockchain.length,
      this.getLatestBlock().hash,
      Date.now(),
      { transactions: this.pendingTransactions },
      ''
    );

    // Proof of work
    while (block.hash.substring(0, this.difficulty) !== Array(this.difficulty + 1).join('0')) {
      block.nonce++;
      block.hash = Block.calculateHash(
        block.index,
        block.previousHash,
        block.timestamp,
        block.data,
        block.nonce
      );
    }

    this.blockchain.push(block);
    this.pendingTransactions = [];
    this.isMining = false;

    // Broadcast new block to peers
    this.broadcastBlock(block);
    this.emit('block:mined', block);
    console.log(`Block #${block.index} mined: ${block.hash}`);
  }

  isChainValid(chain) {
    for (let i = 1; i < chain.length; i++) {
      const currentBlock = chain[i];
      const previousBlock = chain[i - 1];

      if (!Block.isValidBlock(currentBlock, previousBlock)) {
        return false;
      }
    }
    return true;
  }

  replaceChain(newChain) {
    if (newChain.length <= this.blockchain.length) {
      console.log('Received chain is not longer than current chain');
      return false;
    }

    if (!this.isChainValid(newChain)) {
      console.log('Received chain is invalid');
      return false;
    }

    console.log('Replacing current chain with new chain');
    this.blockchain = newChain;
    this.pendingTransactions = [];
    this.emit('chain:replaced', newChain);
    return true;
  }

  // P2P Communication Methods
  broadcastTransaction(transaction) {
    const message = {
      type: 'TRANSACTION',
      data: transaction
    };
    this.peers.forEach(peer => {
      this.sendToPeer(peer, message);
    });
  }

  broadcastBlock(block) {
    const message = {
      type: 'BLOCK',
      data: block
    };
    this.peers.forEach(peer => {
      this.sendToPeer(peer, message);
    });
  }

  requestChain() {
    const message = {
      type: 'REQUEST_CHAIN',
      data: null
    };
    this.peers.forEach(peer => {
      this.sendToPeer(peer, message);
    });
  }

  sendToPeer(peer, message) {
    // Simulated P2P communication - in production use WebSockets, TCP, or libp2p
    console.log(`Sending to ${peer}: ${message.type}`);
    // Actual implementation would use network sockets
    this.emit('message:sent', { peer, message });
  }

  handleMessage(peer, message) {
    switch (message.type) {
      case 'TRANSACTION':
        this.handleTransactionMessage(peer, message.data);
        break;
      case 'BLOCK':
        this.handleBlockMessage(peer, message.data);
        break;
      case 'REQUEST_CHAIN':
        this.handleChainRequest(peer);
        break;
      case 'CHAIN_RESPONSE':
        this.handleChainResponse(peer, message.data);
        break;
      default:
        console.log(`Unknown message type: ${message.type}`);
    }
  }

  handleTransactionMessage(peer, transaction) {
    console.log(`Received transaction from ${peer}`);
    if (!this.pendingTransactions.find(t => t.timestamp === transaction.timestamp)) {
      this.pendingTransactions.push(transaction);
      this.broadcastTransaction(transaction);
    }
  }

  handleBlockMessage(peer, block) {
    console.log(`Received block from ${peer}: #${block.index}`);
    const latestBlock = this.getLatestBlock();
    
    if (block.index === latestBlock.index + 1 && block.previousHash === latestBlock.hash) {
      if (Block.isValidBlock(block, latestBlock)) {
        this.blockchain.push(block);
        this.pendingTransactions = this.pendingTransactions.filter(
          t => !block.data.transactions.find(bt => bt.timestamp === t.timestamp)
        );
        this.broadcastBlock(block);
        this.emit('block:received', block);
      }
    } else if (block.index > latestBlock.index) {
      // We're behind, request full chain
      this.requestChain();
    }
  }

  handleChainRequest(peer) {
    const message = {
      type: 'CHAIN_RESPONSE',
      data: this.blockchain
    };
    this.sendToPeer(peer, message);
  }

  handleChainResponse(peer, chain) {
    console.log(`Received chain from ${peer} with ${chain.length} blocks`);
    this.replaceChain(chain);
  }

  addPeer(peer) {
    if (!this.peers.includes(peer)) {
      this.peers.push(peer);
      console.log(`Added peer: ${peer}`);
      this.requestChain();
    }
  }

  removePeer(peer) {
    this.peers = this.peers.filter(p => p !== peer);
    console.log(`Removed peer: ${peer}`);
  }

  getBlockchain() {
    return this.blockchain;
  }

  getBalance(address) {
    let balance = 0;
    for (const block of this.blockchain) {
      for (const transaction of block.data.transactions) {
        if (transaction.from === address) {
          balance -= transaction.amount;
        }
        if (transaction.to === address) {
          balance += transaction.amount;
        }
      }
    }
    return balance;
  }
}

// Example usage and testing
function testP2PBlockchain() {
  console.log('=== P2P Blockchain Synchronization Test ===\n');

  // Create nodes
  const node1 = new P2PNode(3001, ['peer2:3002', 'peer3:3003']);
  const node2 = new P2PNode(3002, ['peer1:3001', 'peer3:3003']);
  const node3 = new P2PNode(3003, ['peer1:3001', 'peer2:3002']);

  // Add transactions to node1
  console.log('Adding transactions...');
  node1.addTransaction({ from: 'Alice', to: 'Bob', amount: 50, timestamp: Date.now() });
  node1.addTransaction({ from: 'Bob', to: 'Charlie', amount: 25, timestamp: Date.now() + 1 });

  // Mine block on node1
  console.log('\nMining block on node1...');
  node1.minePendingTransactions('Miner1');

  // Simulate P2P communication
  console.log('\nSimulating P2P sync...');
  const minedBlock = node1.getLatestBlock();
  node2.handleMessage('peer1:3001', { type: 'BLOCK', data: minedBlock });
  node3.handleMessage('peer1:3001', { type: 'BLOCK', data: minedBlock });

  // Verify chains are synchronized
  console.log('\n=== Chain Verification ===');
  console.log(`Node1 chain length: ${node1.getBlockchain().length}`);
  console.log(`Node2 chain length: ${node2.getBlockchain().length}`);
  console.log(`Node3 chain length: ${node3.getBlockchain().length}`);

  // Test chain replacement
  console.log('\n=== Chain Replacement Test ===');
  const longerChain = [...node1.getBlockchain()];
  // Add a fake block to make chain longer
  const fakeBlock = new Block(
    3,
    longerChain[2].hash,
    Date.now(),
    { transactions: [], message: 'Fake block' },
    ''
  );
  fakeBlock.hash = Block.calculateHash(
    fakeBlock.index,
    fakeBlock.previousHash,
    fakeBlock.timestamp,
    fakeBlock.data,
    fakeBlock.nonce
  );
  longerChain.push(fakeBlock);

  console.log('Attempting to replace node2 chain with invalid chain...');
  const replaced = node2.replaceChain(longerChain);
  console.log(`Chain replaced: ${replaced}`);

  // Test balance
  console.log('\n=== Balance Check ===');
  console.log(`Miner1 balance: ${node1.getBalance('Miner1')}`);
  console.log(`Alice balance: ${node1.getBalance('Alice')}`);
  console.log(`Bob balance: ${node1.getBalance('Bob')}`);

  console.log('\n=== Test Complete ===');
}

// Run the test
testP2PBlockchain();

// Export for use in other modules
module.exports = {
  P2PNode,
  Block
};
