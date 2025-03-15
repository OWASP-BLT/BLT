class VideoCall {
    constructor() {
        this.roomName = null;
        this.localStream = null;
        this.remoteStream = null;
        this.peerConnection = null;
        this.ws = null;
        this.isInitiator = false;
        this.hasJoinedRoom = false;

        // Audio analysis properties
        this.localAudioContext = null;
        this.localAnalyser = null;
        this.remoteAudioContext = null;
        this.remoteAnalyser = null;
        this.localWaveformData = null;
        this.remoteWaveformData = null;
        this.waveformAnimationId = null;

        // Server status check interval
        this.serverCheckInterval = null;

        // WebRTC configuration
        this.configuration = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' }
            ]
        };

        // Check if we're joining with a room ID from URL
        const urlParams = new URLSearchParams(window.location.search);
        const roomId = urlParams.get('room');

        if (roomId) {
            // We're joining an existing call
            this.initializeCall(roomId, false);
        } else {
            // Show create call button
            this.attachInitialListeners();
        }
    }

    attachInitialListeners() {
        const createRoomBtn = document.getElementById('createRoom');
        const copyLinkBtn = document.getElementById('copyLink');

        if (createRoomBtn) {
            createRoomBtn.addEventListener('click', () => {
                const roomId = Math.random().toString(36).substring(7);
                this.showShareLink(roomId);
                this.initializeCall(roomId, true);
            });
        }

        if (copyLinkBtn) {
            copyLinkBtn.addEventListener('click', () => {
                const shareLink = document.getElementById('shareLink');
                shareLink.select();
                document.execCommand('copy');

                // Show copy confirmation
                const copyConfirm = document.getElementById('copyConfirm');
                copyConfirm.classList.remove('hidden');
                setTimeout(() => copyConfirm.classList.add('hidden'), 2000);
            });
        }
    }

    showShareLink(roomId) {
        // Hide initial controls and show share section
        document.getElementById('initialControls').classList.add('hidden');
        document.getElementById('shareSection').classList.remove('hidden');

        // Set the shareable link
        const shareLink = document.getElementById('shareLink');
        const fullUrl = new URL(window.location.href);
        fullUrl.searchParams.set('room', roomId);
        shareLink.value = fullUrl.toString();
    }

    async initializeCall(roomId, isCreator) {
        this.roomName = roomId;
        this.isInitiator = isCreator;

        // Hide initial sections if they exist
        const initialControls = document.getElementById('initialControls');
        if (initialControls) initialControls.classList.add('hidden');

        // Show call interface
        document.getElementById('callInterface').classList.remove('hidden');

        try {
            await this.setupLocalStream();
            this.setupPeerConnection();
            await this.setupWebSocket();
            this.attachCallListeners();

            // Update connection status
            this.updateConnectionStatus('Waiting for peer to join...');
        } catch (error) {
            console.error('Error initializing call:', error);
            // Show a more detailed error message
            let errorMessage = 'Error initializing call: ';

            if (error.name) {
                // Handle specific error types
                switch (error.name) {
                    case 'NotAllowedError':
                        errorMessage += 'Camera or microphone access denied. Please check permissions.';
                        break;
                    case 'NotFoundError':
                        errorMessage += 'Camera or microphone not found. Please check your devices.';
                        break;
                    case 'NotReadableError':
                        errorMessage += 'Camera or microphone is already in use by another application.';
                        break;
                    case 'AbortError':
                        errorMessage += 'Media capture was aborted.';
                        break;
                    case 'SecurityError':
                        errorMessage += 'Media access is not allowed in this context.';
                        break;
                    default:
                        errorMessage += error.message || error.name || 'Unknown error occurred.';
                }
            } else {
                // If error doesn't have a name property, use the message or toString()
                errorMessage += error.message || error.toString();
            }

            this.updateConnectionStatus(errorMessage);
        }
    }

    updateConnectionStatus(message) {
        const statusDiv = document.getElementById('connectionStatus');
        if (statusDiv) {
            statusDiv.textContent = message;
        }
    }

    setupWebSocket() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/video/${this.roomName}/`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onmessage = async (event) => {
            const data = JSON.parse(event.data);
            try {
                switch (data.type) {
                    case 'room_status':
                        if (data.count > 2) {
                            alert('Room is full!');
                            this.endCall();
                            return;
                        }
                        if (data.count === 2) {
                            this.updateConnectionStatus('Another person has joined the call...');
                        }
                        break;
                    case 'join':
                        if (this.isInitiator && this.hasJoinedRoom) {
                            this.updateConnectionStatus('Peer joined, starting call...');
                            console.log('New peer joined, starting call');
                            await this.startCall();
                        } else {
                            this.hasJoinedRoom = true;
                            this.updateConnectionStatus('Joined call, waiting for connection...');
                            console.log('Joined as peer');
                        }
                        break;
                    case 'offer':
                        this.updateConnectionStatus('Receiving call...');
                        console.log('Received offer, handling...');
                        await this.handleOffer(data);
                        break;
                    case 'answer':
                        this.updateConnectionStatus('Call connected!');
                        console.log('Received answer, handling...');
                        await this.handleAnswer(data);
                        break;
                    case 'ice-candidate':
                        console.log('Received ICE candidate');
                        await this.handleIceCandidate(data);
                        break;
                    case 'peer_disconnected':
                        this.updateConnectionStatus('Other person has left the call');
                        alert('Other person has left the call');
                        this.endCall();
                        break;
                    case 'call_ended':
                        this.updateConnectionStatus('Call has been ended');
                        alert('Call has been ended');
                        this.endCall();
                        break;
                }
            } catch (error) {
                console.error('Error handling WebSocket message:', error);
                this.updateConnectionStatus(`WebSocket message error: ${error.message || 'Unknown error'}`);
            }
        };

        this.ws.onopen = () => {
            console.log('WebSocket connected, joining room:', this.roomName);
            this.ws.send(JSON.stringify({
                type: 'join',
                room: this.roomName
            }));
            this.hasJoinedRoom = true;
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            // WebSocket error event doesn't provide much detail, but we can show what we have
            this.updateConnectionStatus(`WebSocket connection error: ${error.message || 'Connection failed. Please check your network.'}`);
        };

        this.ws.onclose = (event) => {
            console.log('WebSocket closed with code:', event.code);
            if (event.code === 4000) {
                alert('Room is full. Please try again later.');
                window.location.href = window.location.pathname;
            } else {
                this.updateConnectionStatus('Connection closed.');
            }
        };
    }

    async setupLocalStream() {
        try {
            console.log('Requesting media permissions...');
            this.localStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user'
                },
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            console.log('Media access granted:', {
                video: this.localStream.getVideoTracks().length > 0,
                audio: this.localStream.getAudioTracks().length > 0
            });

            const localVideo = document.getElementById('localVideo');
            if (localVideo) {
                localVideo.srcObject = this.localStream;
                await localVideo.play().catch(e => console.error('Error playing local video:', e));

                // Monitor local tracks
                this.localStream.getTracks().forEach(track => {
                    console.log(`Local ${track.kind} track:`, {
                        enabled: track.enabled,
                        muted: track.muted,
                        readyState: track.readyState
                    });
                });
            }

            // Set up audio analysis for local stream
            this.setupAudioAnalysis();
        } catch (error) {
            console.error('Error accessing media devices:', error);
            this.updateConnectionStatus('Error: Could not access camera/microphone. Please check permissions.');
            throw error;
        }
    }

    setupPeerConnection() {
        console.log('Setting up peer connection...');
        this.peerConnection = new RTCPeerConnection({
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' },
                { urls: 'stun:stun2.l.google.com:19302' },
                { urls: 'stun:stun3.l.google.com:19302' },
                { urls: 'stun:stun4.l.google.com:19302' }
            ],
            iceCandidatePoolSize: 10
        });

        // Add local stream tracks to peer connection
        if (this.localStream) {
            console.log('Adding local tracks to peer connection...');
            this.localStream.getTracks().forEach(track => {
                console.log(`Adding ${track.kind} track to peer connection:`, {
                    enabled: track.enabled,
                    muted: track.muted,
                    readyState: track.readyState
                });
                this.peerConnection.addTrack(track, this.localStream);
            });
        } else {
            console.error('No local stream available when setting up peer connection');
            return;
        }

        // Handle remote stream
        this.peerConnection.ontrack = (event) => {
            console.log('Received remote track:', {
                kind: event.track.kind,
                enabled: event.track.enabled,
                muted: event.track.muted,
                readyState: event.track.readyState
            });

            const remoteVideo = document.getElementById('remoteVideo');
            if (remoteVideo && event.streams[0]) {
                console.log('Setting remote stream');
                this.remoteStream = event.streams[0];
                remoteVideo.srcObject = this.remoteStream;

                // Ensure remote video plays
                remoteVideo.play().catch(e => console.error('Error playing remote video:', e));

                // Monitor remote stream
                this.remoteStream.getTracks().forEach(track => {
                    console.log(`Remote ${track.kind} track:`, {
                        enabled: track.enabled,
                        muted: track.muted,
                        readyState: track.readyState
                    });

                    track.onended = () => {
                        console.log(`Remote ${track.kind} track ended`);
                        this.updateConnectionStatus('Remote peer\'s camera/microphone was disconnected');
                    };

                    track.onmute = () => {
                        console.log(`Remote ${track.kind} track muted`);
                        this.updateConnectionStatus('Remote peer muted their camera/microphone');
                    };

                    track.onunmute = () => {
                        console.log(`Remote ${track.kind} track unmuted`);
                        this.updateConnectionStatus('Remote peer unmuted their camera/microphone');
                    };
                });

                // Set up audio analysis for remote stream
                this.setupRemoteAudioAnalysis();

                this.updateConnectionStatus('Connected! Video and audio should start playing.');
            } else {
                console.error('Remote video element or stream not available');
            }
        };

        // Handle ICE candidates
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                console.log('Sending ICE candidate');
                this.ws.send(JSON.stringify({
                    type: 'ice-candidate',
                    candidate: event.candidate
                }));
            }
        };

        this.peerConnection.oniceconnectionstatechange = () => {
            const state = this.peerConnection.iceConnectionState;
            console.log('ICE Connection State:', state);

            switch (state) {
                case 'checking':
                    console.log('Connecting to peer...');
                    this.updateServerStatus('checking');
                    break;
                case 'connected':
                    console.log('Connection established.');
                    // Check which server is being used
                    setTimeout(() => this.checkServerConnection(), 1000);

                    // Start periodic server checks
                    this.startServerChecks();
                    break;
                case 'completed':
                    console.log('Connection completed.');
                    // Check again after completion to get the final server
                    setTimeout(() => this.checkServerConnection(), 1000);
                    break;
                case 'failed':
                    console.error('Connection failed.');
                    this.updateServerStatus('failed');
                    alert('Connection failed. Please try again.');
                    this.endCall();
                    break;
                case 'disconnected':
                    console.log('Peer disconnected');
                    this.updateServerStatus('disconnected');
                    alert('Peer disconnected');
                    break;
                case 'closed':
                    console.log('Connection closed');
                    this.updateServerStatus('disconnected');
                    break;
            }
        };

        this.peerConnection.onconnectionstatechange = () => {
            console.log('Connection state:', this.peerConnection.connectionState);
        };

        this.peerConnection.onsignalingstatechange = () => {
            console.log('Signaling state:', this.peerConnection.signalingState);
        };
    }

    attachCallListeners() {
        const endCallBtn = document.getElementById('endCall');
        const toggleAudioBtn = document.getElementById('toggleAudio');
        const toggleVideoBtn = document.getElementById('toggleVideo');

        if (endCallBtn) {
            endCallBtn.addEventListener('click', () => {
                // Add confirmation dialog before ending the call with a clear message
                if (confirm('Are you sure you want to end this call? This will disconnect both participants.')) {
                    this.endCall();
                }
            });
        }

        if (toggleAudioBtn) toggleAudioBtn.addEventListener('click', () => this.toggleAudio());
        if (toggleVideoBtn) toggleVideoBtn.addEventListener('click', () => this.toggleVideo());
    }

    async startCall() {
        try {
            if (!this.peerConnection) {
                console.log('Creating new peer connection for call start');
                this.setupPeerConnection();
            }

            // Create and set transceivers for bidirectional media
            const audioTransceiver = this.peerConnection.addTransceiver('audio', {
                direction: 'sendrecv',
                streams: [this.localStream]
            });

            const videoTransceiver = this.peerConnection.addTransceiver('video', {
                direction: 'sendrecv',
                streams: [this.localStream]
            });

            console.log('Creating offer...');
            const offer = await this.peerConnection.createOffer({
                offerToReceiveAudio: true,
                offerToReceiveVideo: true
            });

            console.log('Setting local description...');
            await this.peerConnection.setLocalDescription(offer);

            console.log('Sending offer...');
            this.ws.send(JSON.stringify({
                type: 'offer',
                offer: offer
            }));
        } catch (error) {
            console.error('Error starting call:', error);
            this.updateConnectionStatus(`Error starting call: ${error.message || 'Failed to create or send offer'}`);
        }
    }

    async handleOffer(data) {
        try {
            if (!this.peerConnection) {
                this.setupPeerConnection();
            }

            if (!this.localStream) {
                console.error('Local stream not available');
                return;
            }

            console.log('Setting remote description from offer...');
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));

            console.log('Creating answer...');
            const answer = await this.peerConnection.createAnswer();

            console.log('Setting local description...');
            await this.peerConnection.setLocalDescription(answer);

            console.log('Sending answer...');
            this.ws.send(JSON.stringify({
                type: 'answer',
                answer: answer
            }));
        } catch (error) {
            console.error('Error handling offer:', error);
            alert('Error connecting to peer. Please try again.');
        }
    }

    async handleAnswer(data) {
        try {
            if (!this.peerConnection) {
                console.error('No peer connection when receiving answer');
                return;
            }

            const description = new RTCSessionDescription(data.answer);
            const signalingState = this.peerConnection.signalingState;
            console.log('Current signaling state:', signalingState);

            if (signalingState === "have-local-offer") {
                console.log('Setting remote description from answer...');
                await this.peerConnection.setRemoteDescription(description);
            } else {
                console.warn('Received answer in wrong signaling state:', signalingState);
            }
        } catch (error) {
            console.error('Error handling answer:', error);
        }
    }

    async handleIceCandidate(data) {
        try {
            if (data.candidate && this.peerConnection) {
                await this.peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
            }
        } catch (error) {
            console.error('Error handling ICE candidate:', error);
        }
    }

    toggleAudio() {
        if (this.localStream) {
            const audioTrack = this.localStream.getAudioTracks()[0];
            if (audioTrack) {
                audioTrack.enabled = !audioTrack.enabled;
                const toggleAudioBtn = document.getElementById('toggleAudio');
                if (toggleAudioBtn) {
                    toggleAudioBtn.textContent = audioTrack.enabled ? 'Mute Audio' : 'Unmute Audio';
                }
            }
        }
    }

    toggleVideo() {
        if (this.localStream) {
            const videoTrack = this.localStream.getVideoTracks()[0];
            if (videoTrack) {
                videoTrack.enabled = !videoTrack.enabled;
                const toggleVideoBtn = document.getElementById('toggleVideo');
                if (toggleVideoBtn) {
                    toggleVideoBtn.textContent = videoTrack.enabled ? 'Turn Off Video' : 'Turn On Video';
                }
            }
        }
    }

    endCall() {
        // Notify others before closing connection
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'end_call'
            }));
        }

        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
        }
        if (this.ws) {
            this.ws.close();
        }

        // Stop server checks
        this.stopServerChecks();

        // Clean up audio analysis resources
        if (this.waveformAnimationId) {
            cancelAnimationFrame(this.waveformAnimationId);
            this.waveformAnimationId = null;
        }

        if (this.localAudioContext) {
            this.localAudioContext.close().catch(e => console.error('Error closing local audio context:', e));
            this.localAudioContext = null;
            this.localAnalyser = null;
            this.localWaveformData = null;
        }

        if (this.remoteAudioContext) {
            this.remoteAudioContext.close().catch(e => console.error('Error closing remote audio context:', e));
            this.remoteAudioContext = null;
            this.remoteAnalyser = null;
            this.remoteWaveformData = null;
        }

        // Redirect to base URL without room parameter
        window.location.href = window.location.pathname;
    }

    setupAudioAnalysis() {
        // Set up local audio analysis
        if (this.localStream && this.localStream.getAudioTracks().length > 0) {
            try {
                this.localAudioContext = new (window.AudioContext || window.webkitAudioContext)();
                this.localAnalyser = this.localAudioContext.createAnalyser();
                this.localAnalyser.fftSize = 32; // Small FFT size for a simple visualization

                const localSource = this.localAudioContext.createMediaStreamSource(this.localStream);
                localSource.connect(this.localAnalyser);

                // Create data array for waveform
                this.localWaveformData = new Uint8Array(this.localAnalyser.frequencyBinCount);

                console.log('Local audio analysis set up successfully');
            } catch (error) {
                console.error('Error setting up local audio analysis:', error);
            }
        }

        // Start animation loop for waveforms
        this.startWaveformAnimation();
    }

    setupRemoteAudioAnalysis() {
        // Set up remote audio analysis when remote stream is available
        if (this.remoteStream && this.remoteStream.getAudioTracks().length > 0) {
            try {
                this.remoteAudioContext = new (window.AudioContext || window.webkitAudioContext)();
                this.remoteAnalyser = this.remoteAudioContext.createAnalyser();
                this.remoteAnalyser.fftSize = 32; // Small FFT size for a simple visualization

                const remoteSource = this.remoteAudioContext.createMediaStreamSource(this.remoteStream);
                remoteSource.connect(this.remoteAnalyser);

                // Create data array for waveform
                this.remoteWaveformData = new Uint8Array(this.remoteAnalyser.frequencyBinCount);

                console.log('Remote audio analysis set up successfully');
            } catch (error) {
                console.error('Error setting up remote audio analysis:', error);
            }
        }
    }

    startWaveformAnimation() {
        // Cancel any existing animation
        if (this.waveformAnimationId) {
            cancelAnimationFrame(this.waveformAnimationId);
        }

        const updateWaveforms = () => {
            this.updateWaveform('local');
            this.updateWaveform('remote');
            this.waveformAnimationId = requestAnimationFrame(updateWaveforms);
        };

        this.waveformAnimationId = requestAnimationFrame(updateWaveforms);
    }

    updateWaveform(type) {
        const waveformElement = document.getElementById(`${type}Waveform`);
        if (!waveformElement) return;

        let analyser, waveformData;

        if (type === 'local') {
            analyser = this.localAnalyser;
            waveformData = this.localWaveformData;
        } else {
            analyser = this.remoteAnalyser;
            waveformData = this.remoteWaveformData;
        }

        if (!analyser || !waveformData) return;

        // Get frequency data
        analyser.getByteFrequencyData(waveformData);

        // Calculate average volume level (0-255)
        let sum = 0;
        for (let i = 0; i < waveformData.length; i++) {
            sum += waveformData[i];
        }
        const average = sum / waveformData.length;

        // Create or update waveform bars
        const numBars = 5;

        // Clear existing bars
        waveformElement.innerHTML = '';

        // Create new bars based on audio level
        for (let i = 0; i < numBars; i++) {
            const bar = document.createElement('div');

            // Calculate height based on audio level and position
            // Center bars are taller than edge bars
            const position = Math.abs(i - (numBars - 1) / 2) / ((numBars - 1) / 2);
            const baseHeight = Math.max(1, Math.min(20, average / 255 * 20));
            const height = baseHeight * (1 - 0.5 * position);

            bar.className = 'bg-[#e74c3c] rounded-full transition-all duration-100';
            bar.style.width = '2px';
            bar.style.height = `${height}px`;

            waveformElement.appendChild(bar);
        }
    }

    updateServerStatus(status, serverType = null) {
        const serverStatusDiv = document.getElementById('serverStatus');
        if (!serverStatusDiv) return;

        const statusDot = serverStatusDiv.querySelector('div');
        const statusText = serverStatusDiv.querySelector('span');

        if (status === 'checking') {
            statusDot.className = 'w-2 h-2 rounded-full bg-yellow-400';
            statusText.textContent = 'Server: Checking...';
        } else if (status === 'connected') {
            statusDot.className = 'w-2 h-2 rounded-full bg-green-500';
            statusText.textContent = `Server: ${serverType || 'Connected'}`;
        } else if (status === 'disconnected') {
            statusDot.className = 'w-2 h-2 rounded-full bg-red-500';
            statusText.textContent = 'Server: Disconnected';
        } else if (status === 'failed') {
            statusDot.className = 'w-2 h-2 rounded-full bg-red-500';
            statusText.textContent = 'Server: Connection Failed';
        }
    }

    async checkServerConnection() {
        if (!this.peerConnection) return;

        try {
            // Get stats to determine which ICE candidate pair is being used
            const stats = await this.peerConnection.getStats();
            let activeCandidatePair = null;
            let localCandidate = null;
            let remoteCandidate = null;

            stats.forEach(report => {
                if (report.type === 'transport') {
                    console.log('Transport stats:', report);
                }

                // Find the active candidate pair
                if (report.type === 'candidate-pair' && report.state === 'succeeded') {
                    activeCandidatePair = report;
                    console.log('Active candidate pair:', report);
                }

                // Collect local candidates
                if (report.type === 'local-candidate') {
                    if (activeCandidatePair && report.id === activeCandidatePair.localCandidateId) {
                        localCandidate = report;
                        console.log('Local candidate:', report);
                    }
                }

                // Collect remote candidates
                if (report.type === 'remote-candidate') {
                    if (activeCandidatePair && report.id === activeCandidatePair.remoteCandidateId) {
                        remoteCandidate = report;
                        console.log('Remote candidate:', report);
                    }
                }
            });

            if (localCandidate && remoteCandidate) {
                let serverType = 'Unknown';

                // Determine connection type based on candidate types
                if (localCandidate.candidateType === 'host' && remoteCandidate.candidateType === 'host') {
                    serverType = 'Direct P2P';
                } else if (localCandidate.candidateType === 'srflx' || remoteCandidate.candidateType === 'srflx') {
                    serverType = 'STUN (NAT)';
                } else if (localCandidate.candidateType === 'relay' || remoteCandidate.candidateType === 'relay') {
                    serverType = 'TURN Relay';
                }

                // Update server status with the determined type
                this.updateServerStatus('connected', serverType);

                // Log connection details
                console.log(`Connection type: ${serverType}`);
                console.log(`Local candidate type: ${localCandidate.candidateType}`);
                console.log(`Remote candidate type: ${remoteCandidate.candidateType}`);

                if (localCandidate.ip) {
                    console.log(`Local IP: ${this.maskIP(localCandidate.ip)}`);
                }
                if (remoteCandidate.ip) {
                    console.log(`Remote IP: ${this.maskIP(remoteCandidate.ip)}`);
                }
            } else {
                this.updateServerStatus('checking');
            }
        } catch (error) {
            console.error('Error checking server connection:', error);
            this.updateServerStatus('checking');
        }
    }

    // Helper method to mask IP addresses for privacy in logs
    maskIP(ip) {
        if (!ip) return 'unknown';

        // For IPv4
        if (ip.includes('.')) {
            const parts = ip.split('.');
            return `${parts[0]}.${parts[1]}.*.*`;
        }

        // For IPv6
        if (ip.includes(':')) {
            const parts = ip.split(':');
            return `${parts[0]}:${parts[1]}:****:****`;
        }

        return ip;
    }

    startServerChecks() {
        // Clear any existing interval
        this.stopServerChecks();

        // Check server status every 30 seconds
        this.serverCheckInterval = setInterval(() => {
            if (this.peerConnection &&
                (this.peerConnection.iceConnectionState === 'connected' ||
                    this.peerConnection.iceConnectionState === 'completed')) {
                this.checkServerConnection();
            }
        }, 30000); // 30 seconds
    }

    stopServerChecks() {
        if (this.serverCheckInterval) {
            clearInterval(this.serverCheckInterval);
            this.serverCheckInterval = null;
        }
    }
}

// Initialize video call when page loads
document.addEventListener('DOMContentLoaded', () => {
    new VideoCall();
});

