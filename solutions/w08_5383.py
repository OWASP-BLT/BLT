// file: blockchain-p2p-network.js
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
    return crypto.createHash('sha256').update(
      this.index + this.timestamp + JSON.stringify(this.data) + this.previousHash + this.nonce
    ).digest('hex');
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
    this.difficulty = 4;
    this.pendingTransactions = [];
    this.miningReward = 100;
    this.nodes = new Set();
  }

  createGenesisBlock() {
    return new Block(0, Date.now(), 'Genesis Block', '0');
  }

  getLatestBlock() {
    return this.chain[this.chain.length - 1];
  }

  minePendingTransactions(miningRewardAddress) {
    const rewardTx = {
      from: null,
      to: miningRewardAddress,
      amount: this.miningReward
    };
    this.pendingTransactions.push(rewardTx);

    const block = new Block(
      this.chain.length,
      Date.now(),
      this.pendingTransactions,
      this.getLatestBlock().hash
    );
    block.mineBlock(this.difficulty);

    console.log('Block successfully mined!');
    this.chain.push(block);
    this.pendingTransactions = [];
  }

  createTransaction(transaction) {
    this.pendingTransactions.push(transaction);
  }

  getBalanceOfAddress(address) {
    let balance = 0;
    for (const block of this.chain) {
      for (const trans of block.data) {
        if (trans.from === address) {
          balance -= trans.amount;
        }
        if (trans.to === address) {
          balance += trans.amount;
        }
      }
    }
    return balance;
  }

  isChainValid() {
    for (let i = 1; i < this.chain.length; i++) {
      const currentBlock = this.chain[i];
      const previousBlock = this.chain[i - 1];

      if (currentBlock.hash !== currentBlock.calculateHash()) {
        return false;
      }
      if (currentBlock.previousHash !== previousBlock.hash) {
        return false;
      }
    }
    return true;
  }

  addNode(address) {
    this.nodes.add(address);
  }

  removeNode(address) {
    this.nodes.delete(address);
  }

  getNodes() {
    return Array.from(this.nodes);
  }
}

class P2PNode extends EventEmitter {
  constructor(port, blockchain) {
    super();
    this.port = port;
    this.blockchain = blockchain;
    this.peers = new Map();
    this.server = null;
    this.isRunning = false;
  }

  start() {
    this.server = net.createServer((socket) => {
      this.handleConnection(socket);
    });

    this.server.listen(this.port, () => {
      this.isRunning = true;
      console.log(`P2P Node listening on port ${this.port}`);
      this.emit('started', this.port);
    });

    this.server.on('error', (err) => {
      console.error(`Server error: ${err.message}`);
      this.emit('error', err);
    });
  }

  stop() {
    if (this.server) {
      this.server.close(() => {
        this.isRunning = false;
        console.log('P2P Node stopped');
        this.emit('stopped');
      });
    }
    for (const [address, socket] of this.peers) {
      socket.end();
    }
    this.peers.clear();
  }

  connectToPeer(host, port) {
    const client = new net.Socket();
    const peerAddress = `${host}:${port}`;

    client.connect(port, host, () => {
      console.log(`Connected to peer ${peerAddress}`);
      this.peers.set(peerAddress, client);
      this.emit('peerConnected', peerAddress);
      this.sendMessage(client, { type: 'handshake', port: this.port });
    });

    client.on('data', (data) => {
      this.handleData(client, data);
    });

    client.on('close', () => {
      console.log(`Connection to ${peerAddress} closed`);
      this.peers.delete(peerAddress);
      this.emit('peerDisconnected', peerAddress);
    });

    client.on('error', (err) => {
      console.error(`Connection error to ${peerAddress}: ${err.message}`);
      this.peers.delete(peerAddress);
      this.emit('peerError', peerAddress, err);
    });
  }

  handleConnection(socket) {
    const remoteAddress = `${socket.remoteAddress}:${socket.remotePort}`;
    console.log(`New connection from ${remoteAddress}`);

    socket.on('data', (data) => {
      this.handleData(socket, data);
    });

    socket.on('close', () => {
      console.log(`Connection from ${remoteAddress} closed`);
      for (const [address, s] of this.peers) {
        if (s === socket) {
          this.peers.delete(address);
          break;
        }
      }
      this.emit('peerDisconnected', remoteAddress);
    });

    socket.on('error', (err) => {
      console.error(`Socket error: ${err.message}`);
    });
  }

  handleData(socket, data) {
    try {
      const message = JSON.parse(data.toString());
      this.processMessage(socket, message);
    } catch (err) {
      console.error('Invalid message format:', err.message);
    }
  }

  sendMessage(socket, message) {
    const data = JSON.stringify(message);
    socket.write(data);
  }

  broadcast(message) {
    for (const [address, socket] of this.peers) {
      this.sendMessage(socket, message);
    }
  }

  processMessage(socket, message) {
    switch (message.type) {
      case 'handshake':
        const peerAddress = `${socket.remoteAddress}:${message.port}`;
        if (!this.peers.has(peerAddress)) {
          this.peers.set(peerAddress, socket);
          this.emit('peerConnected', peerAddress);
          this.sendMessage(socket, { type: 'handshake_ack', port: this.port });
        }
        break;

      case 'handshake_ack':
        console.log('Handshake acknowledged');
        break;

      case 'new_block':
        this.handleNewBlock(message.block);
        break;

      case 'new_transaction':
        this.handleNewTransaction(message.transaction);
        break;

      case 'chain_request':
        this.sendMessage(socket, {
          type: 'chain_response',
          chain: this.blockchain.chain
        });
        break;

      case 'chain_response':
        this.handleChainResponse(message.chain);
        break;

      case 'peer_list':
        this.handlePeerList(message.peers);
        break;

      default:
        console.log('Unknown message type:', message.type);
    }
  }

  handleNewBlock(block) {
    console.log('Received new block:', block.hash);
    const lastBlock = this.blockchain.getLatestBlock();
    if (lastBlock.hash === block.previousHash && block.hash === block.calculateHash()) {
      this.blockchain.chain.push(block);
      this.broadcast({ type: 'new_block', block });
      this.emit('blockAdded', block);
    } else {
      console.log('Invalid block received, requesting chain sync');
      this.requestChain();
    }
  }

  handleNewTransaction(transaction) {
    console.log('Received new transaction');
    this.blockchain.createTransaction(transaction);
    this.broadcast({ type: 'new_transaction', transaction });
    this.emit('transactionAdded', transaction);
  }

  handleChainResponse(chain) {
    console.log('Received chain response');
    if (chain.length > this.blockchain.chain.length) {
      const receivedChain = chain.map(blockData => {
        const block = new Block(
          blockData.index,
          blockData.timestamp,
          blockData.data,
          blockData.previousHash
        );
        block.hash = blockData.hash;
        block.nonce = blockData.nonce;
        return block;
      });

      const tempBlockchain = new Blockchain();
      tempBlockchain.chain = receivedChain;

      if (tempBlockchain.isChainValid()) {
        this.blockchain.chain = receivedChain;
        console.log('Chain updated with longer chain');
        this.emit('chainUpdated');
      } else {
        console.log('Received chain is invalid');
      }
    }
  }

  handlePeerList(peers) {
    console.log('Received peer list');
    peers.forEach(peer => {
      const [host, port] = peer.split(':');
      if (!this.peers.has(peer) && host !== '127.0.0.1' && host !== 'localhost') {
        this.connectToPeer(host, parseInt(port));
      }
    });
  }

  requestChain() {
    this.broadcast({ type: 'chain_request' });
  }

  broadcastNewBlock(block) {
    this.broadcast({ type: 'new_block', block });
  }

  broadcastNewTransaction(transaction) {
    this.broadcast({ type: 'new_transaction', transaction });
  }

  broadcastPeerList() {
    const peers = Array.from(this.peers.keys());
    this.broadcast({ type: 'peer_list', peers });
  }

  getConnectedPeers() {
    return Array.from(this.peers.keys());
  }
}

// Example usage
function main() {
  const blockchain = new Blockchain();
  const node1 = new P2PNode(3001, blockchain);
  const node2 = new P2PNode(3002, blockchain);

  node1.start();
  node2.start();

  // Connect nodes after a short delay
  setTimeout(() => {
    node1.connectToPeer('127.0.0.1', 3002);
  }, 1000);

  // Create and broadcast a transaction
  setTimeout(() => {
    const transaction = {
      from: 'address1',
      to: 'address2',
      amount: 50
    };
    blockchain.createTransaction(transaction);
    node1.broadcastNewTransaction(transaction);
  }, 2000);

  // Mine a block
  setTimeout(() => {
    blockchain.minePendingTransactions('miner_address');
    const latestBlock = blockchain.getLatestBlock();
    node1.broadcastNewBlock(latestBlock);
  }, 3000);

  // Display blockchain state
  setTimeout(() => {
    console.log('Blockchain:');
    console.log(JSON.stringify(blockchain.chain, null, 2));
    console.log('Connected peers:', node1.getConnectedPeers());
    console.log('Is chain valid:', blockchain.isChainValid());
  }, 4000);
}

if (require.main === module) {
  main();
}

module.exports = { Block, Blockchain, P2PNode };
