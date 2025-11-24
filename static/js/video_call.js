// Update connection status indicators
async function updateConnectionInfo(pc) {
    if (!pc) {
        return;
    }

    // Check P2P status
    const p2pDot = document.querySelector('#p2pStatus div');
    const p2pText = document.querySelector('#p2pStatus span');
    
    if (pc.iceConnectionState === 'connected' || pc.iceConnectionState === 'completed') {
        try {
            const stats = await pc.getStats();
            let isP2P = true;
            let hasActiveConnection = false;

            stats.forEach(report => {
                if (report.type === 'candidate-pair' && report.state === 'succeeded') {
                    hasActiveConnection = true;
                    
                    // Get the local and remote candidates
                    const localCandidate = stats.get(report.localCandidateId);
                    const remoteCandidate = stats.get(report.remoteCandidateId);

                    if (localCandidate?.candidateType === 'relay' || remoteCandidate?.candidateType === 'relay') {
                        isP2P = false;
                    }
                }
            });

            if (hasActiveConnection) {
                p2pDot.className = `w-2 h-2 rounded-full ${isP2P ? 'bg-green-500' : 'bg-yellow-500'}`;
                p2pText.textContent = `P2P: ${isP2P ? 'Direct Connection' : 'Using TURN Server'}`;
            } else {
                p2pDot.className = 'w-2 h-2 rounded-full bg-gray-300';
                p2pText.textContent = 'P2P: Checking...';
            }
        } catch (error) {
            console.error('Error getting connection stats:', error);
            p2pDot.className = 'w-2 h-2 rounded-full bg-red-500';
            p2pText.textContent = 'P2P: Status Unknown';
        }
    } else {
        p2pDot.className = 'w-2 h-2 rounded-full bg-gray-300';
        p2pText.textContent = 'P2P: Checking...';
    }
}

// Add periodic status updates
function startStatusUpdates(pc) {
    // Initial update
    updateConnectionInfo(pc);

    const updateInterval = setInterval(async () => {
        if (pc.iceConnectionState === 'connected' || pc.iceConnectionState === 'completed') {
            await updateConnectionInfo(pc);
        } else if (pc.connectionState === 'closed' || pc.connectionState === 'failed') {
            clearInterval(updateInterval);
        }
    }, 2000); // Update every 2 seconds

    // Clean up interval when connection closes
    pc.addEventListener('connectionstatechange', () => {
        if (pc.connectionState === 'closed' || pc.connectionState === 'failed') {
            clearInterval(updateInterval);
        }
    });

    // Also update on ICE connection state changes
    pc.addEventListener('iceconnectionstatechange', () => {
        updateConnectionInfo(pc);
    });
}

// Update your existing connection state change handler
peerConnection.onconnectionstatechange = () => {
    const state = peerConnection.connectionState;
    const statusDiv = document.getElementById('connectionStatus');
    
    switch (state) {
        case 'connecting':
            statusDiv.textContent = 'Connecting to peer...';
            break;
        case 'connected':
            statusDiv.textContent = 'Connected!';
            updateConnectionInfo(peerConnection);
            startStatusUpdates(peerConnection);
            break;
        case 'disconnected':
            statusDiv.textContent = 'Disconnected from peer.';
            break;
        case 'failed':
            statusDiv.textContent = 'Connection failed.';
            break;
        default:
            statusDiv.textContent = `Connection state: ${state}`;
    }
};

// Also update when ICE gathering state changes
peerConnection.oniceconnectionstatechange = () => {
    updateConnectionInfo(peerConnection);
};

// Add this to your existing connection setup code
peerConnection.addEventListener('negotiationneeded', () => {
    updateConnectionInfo(peerConnection);
}); 
