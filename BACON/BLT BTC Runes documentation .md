# Documentation for etching runes for BACON

**31 Jan, 2025\.**  
**1:30AM IST.**

Right now, we have three servers with alphaVPS as the provider.

One node runs a regtest, where we etched the BTC runes(BLT•BACON•TOKENS) initially for POC purposes 

And two others are syncing up with the mainnet, where we plan to etch the BACON token again.

**The current state while writing:**  
1\. Regtest and ord server are running peacefully and all the operations are getting handled smoothly.

2\. The mainnet1 has synced upto 90% and the mainnet2 has synced upto 70% as of now.

**Current Workflow**

1. On the regtest node, we have a regtest.service daemon process running the bitcoin blockchain and the ord-flask.service daemon running for interaction of sending bacon tokens to the users submitted in /send-bacon-tokens endpoint ,tmux process on bitcoin user running the ordinal server to index the blocks on regtest and perform wallet operations(creating wallet, etching runes, transferring funds).
2. First we will do a complete integration with the regtest , and once the mainnet spins up , we'll run an ord server that index the mainnet blocks and perform wallet operations.

**Some useful references:**  
[https://ordtutorial.vercel.app/ordtestnet](https://ordtutorial.vercel.app/ordtestnet) 
The ordicord discord server 

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

**Command to start the bitcoind process on the mainnet, as we use the bitcoind snap package on this server.**  
bitcoin-core.daemon \-datadir=/home/apoorva/test-btc-data \-dbcache=256 \-rpcworkqueue=1000

**Some additional observations:**

1. I found that ^C takes a lot of time to stop the bitcoind process,so another way to kill it instantly is finding the PID of the bitcoind process and killing it, saves a lot of time, but use with caution, since it might corrupt the indexing and syncing.


