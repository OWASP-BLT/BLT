// blockchain-p2p-network.js
const crypto = require('crypto');
const net = require('net');
const EventEmitter = require('events');

class Block {
  constructor(index, timestamp, data, previousHash = '') {
    this.index = index;
    this.timestamp = timestamp;
    this.data = data;
    this.previousHash = previousHash;
    this.hash = this.calculateHash();
    this.nonce = 0;
  }

  calculateHash() {
    return crypto.createHash('sha256')
      .update(this.index + this.timestamp + JSON.stringify(this.data) + this.previousHash + this.nonce)
      .digest('hex');
  }

  mineBlock(difficulty) {
    while (this.hash.substring(0, difficulty) !== Array(difficulty + 1).join('0')) {
      this.nonce++;
      this.hash = this.calculateHash();
    }
    console.log(`Block mined: ${this.hash}`);
  }
}

class Blockchain {
  constructor() {
    this.chain = [this.createGenesisBlock()];
    this.difficulty = 2;
    this.pendingTransactions = [];
    this.miningReward = 100;
    this.nodes = new Set();
    this.peers = new Map();
    this.server = null;
    this.eventEmitter = new EventEmitter();
  }

  createGenesisBlock() {
    return new Block(0, Date.now(), 'Genesis Block', '0');
  }

  getLatestBlock() {
    return this.chain[this.chain.length - 1];
  }

  addTransaction(transaction) {
    this.pendingTransactions.push(transaction);
  }

  minePendingTransactions(miningRewardAddress) {
    const block = new Block(
      this.chain.length,
      Date.now(),
      this.pendingTransactions,
      this.getLatestBlock().hash
    );
    block.mineBlock(this.difficulty);
    this.chain.push(block);
    this.pendingTransactions = [
      { from: null, to: miningRewardAddress, amount: this.miningReward }
    ];
    this.broadcastBlock(block);
  }

  isChainValid(chain) {
    for (let i = 1; i < chain.length; i++) {
      const currentBlock = chain[i];
      const previousBlock = chain[i - 1];

      if (currentBlock.hash !== currentBlock.calculateHash()) return false;
      if (currentBlock.previousHash !== previousBlock.hash) return false;
    }
    return true;
  }

  replaceChain(newChain) {
    if (newChain.length > this.chain.length && this.isChainValid(newChain)) {
      console.log('Replacing chain with new chain');
      this.chain = newChain;
      this.eventEmitter.emit('chainUpdated', this.chain);
    } else {
      console.log('Received chain invalid or shorter');
    }
  }

  // P2P Network Methods
  startServer(port) {
    this.server = net.createServer((socket) => {
      this.handleConnection(socket);
    });
    this.server.listen(port, () => {
      console.log(`Server listening on port ${port}`);
    });
  }

  connectToPeer(host, port) {
    const socket = new net.Socket();
    socket.connect(port, host, () => {
      console.log(`Connected to peer ${host}:${port}`);
      this.handleConnection(socket);
      this.sendMessage(socket, { type: 'handshake', data: { address: `${this.getLocalIP()}:${this.server?.address().port}` } });
    });
    socket.on('error', (err) => {
      console.error(`Connection error to ${host}:${port}:`, err.message);
    });
  }

  handleConnection(socket) {
    const peerAddress = `${socket.remoteAddress}:${socket.remotePort}`;
    console.log(`New connection from ${peerAddress}`);
    this.peers.set(peerAddress, socket);

    socket.on('data', (data) => {
      try {
        const message = JSON.parse(data.toString());
        this.handleMessage(socket, message);
      } catch (err) {
        console.error('Invalid message:', err);
      }
    });

    socket.on('close', () => {
      console.log(`Connection closed: ${peerAddress}`);
      this.peers.delete(peerAddress);
    });

    socket.on('error', (err) => {
      console.error(`Socket error: ${err.message}`);
      this.peers.delete(peerAddress);
    });
  }

  handleMessage(socket, message) {
    switch (message.type) {
      case 'handshake':
        console.log(`Handshake received from ${message.data.address}`);
        this.nodes.add(message.data.address);
        this.sendMessage(socket, { type: 'handshake_ack', data: { address: `${this.getLocalIP()}:${this.server?.address().port}` } });
        this.sendMessage(socket, { type: 'chain', data: this.chain });
        break;
      case 'handshake_ack':
        console.log(`Handshake acknowledged from ${message.data.address}`);
        this.nodes.add(message.data.address);
        break;
      case 'chain':
        console.log('Received chain from peer');
        this.replaceChain(message.data);
        break;
      case 'new_block':
        console.log('Received new block from peer');
        this.addBlockFromPeer(message.data);
        break;
      case 'new_transaction':
        console.log('Received new transaction from peer');
        this.addTransaction(message.data);
        break;
      default:
        console.log('Unknown message type:', message.type);
    }
  }

  sendMessage(socket, message) {
    const data = JSON.stringify(message);
    socket.write(data);
  }

  broadcastMessage(message) {
    this.peers.forEach((socket) => {
      this.sendMessage(socket, message);
    });
  }

  broadcastBlock(block) {
    this.broadcastMessage({ type: 'new_block', data: block });
  }

  broadcastTransaction(transaction) {
    this.broadcastMessage({ type: 'new_transaction', data: transaction });
  }

  addBlockFromPeer(block) {
    const latestBlock = this.getLatestBlock();
    if (block.previousHash === latestBlock.hash && block.index === latestBlock.index + 1) {
      this.chain.push(block);
      this.eventEmitter.emit('chainUpdated', this.chain);
      console.log('Block added from peer');
    } else {
      console.log('Invalid block from peer');
    }
  }

  getLocalIP() {
    const interfaces = require('os').networkInterfaces();
    for (const name of Object.keys(interfaces)) {
      for (const iface of interfaces[name]) {
        if (iface.family === 'IPv4' && !iface.internal) {
          return iface.address;
        }
      }
    }
    return '127.0.0.1';
  }

  getBalance(address) {
    let balance = 0;
    for (const block of this.chain) {
      for (const trans of block.data) {
        if (trans.from === address) balance -= trans.amount;
        if (trans.to === address) balance += trans.amount;
      }
    }
    return balance;
  }

  getChainInfo() {
    return {
      length: this.chain.length,
      difficulty: this.difficulty,
      miningReward: this.miningReward,
      pendingTransactions: this.pendingTransactions.length,
      peers: this.peers.size,
      nodes: this.nodes.size
    };
  }
}

// Example usage
const blockchain = new Blockchain();

// Start P2P server
blockchain.startServer(8333);

// Connect to a peer (example)
// blockchain.connectToPeer('192.168.1.100', 8333);

// Add transactions and mine
blockchain.addTransaction({ from: 'address1', to: 'address2', amount: 10 });
blockchain.addTransaction({ from: 'address2', to: 'address3', amount: 5 });

console.log('Starting mining...');
blockchain.minePendingTransactions('miner-address');

console.log('Balance of miner:', blockchain.getBalance('miner-address'));
console.log('Chain info:', blockchain.getChainInfo());

// Export for use in other modules
module.exports = { Blockchain, Block };
