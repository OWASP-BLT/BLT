# Documentation for etching runes for BACON

**2 Jan, 2025\.**  
**11AM IST.**

Right now, we have two servers with alphaVPS as the provider.

One node runs a testnet, where we plan to etch the BTC runes initially for POC purposes.

And another one is syncing up with the mainnet, where we plan to etch the BACON token.

**The current state while writing:**  
1\. Testnet server has a corrupted chain index (started reindexing today), due to random killing of the bitcoind process, we might have to raise a ticket with alphaVPS for this, since its probable they do this because of I/O limits.

2\. The mainnet is syncing slow and steady and is upto \~46.5% as of writing.

**Current Workflow**

1. On the testnet node, one tmux session is used to run the node and other is used to run the ord server.  
2. Once both of these sync up, we will probably create another tmux session to create wallet and etch runes.  
3. On the mainnet node, we just have a single tmux session as of writing where the bitcoind process is syncing the node with the mainnet.

**Some useful references:**  
[https://ordtutorial.vercel.app/ordtestnet](https://ordtutorial.vercel.app/ordtestnet) 

**Current bitcoind config on testnet.**  
server=1  
testnet=1  
txindex=1  
rpcuser=apoorva  
blockfilterindex=1  
rpcpassword=y^2DhUnxrhFr7qAj2yjhvykFz  
rpcallowip=127.0.0.1
[test]  
rpcport=8332  
rpcbind=127.0.0.1  

**Current bitcoind config on the mainnet:**  
server=1  
txindex=1  
rpcuser=apoorva  
blockfilterindex=1  
rpcpassword=y^2DhUnxrhFr7qAj2yjhvykFz  
rpcallowip=127.0.0.1  
rpcport=8332  
blockfilterindex=1

Side note: We might want to add rpcbind here after the node syncs completely.

**Command to start the bitcoind process on the testnet, note that we use the bitcoind snap package on both our servers.**  
bitcoin-core.daemon \-datadir=/home/apoorva/test-btc-data \-dbcache=256 \-rpcworkqueue=1000

**Command to start the ordinal server to index blocks after syncing the node completely, we will create a wallet and etch runes once this completes.**  
sudo ./ord \--bitcoin-rpc-user apoorva \--bitcoin-rpc-pass y^2DhUnxrhFr7qAj2yjhvykFz \--rpc-url http://127.0.0.1:8332 \--data-dir /home/apoorva/ord-data \--bitcoin-data-dir /home/apoorva/test-btc-data \--index-runes \--testnet \--verbose server

**Some additional observations:**

1. I found that ^C takes a lot of time to stop the bitcoind process,so another way to kill it instantly is finding the PID of the bitcoind process and killing it, saves a lot of time, but use with caution, since it might corrupt the indexing and syncing.

