import { useState, useEffect, useRef, useCallback } from 'react';

export type WebSocketMessage = {
  type: string;
  data: any;
};

export interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number;
  reconnectAttempts?: number;
}

export interface UseWebSocketReturn {
  sendMessage: (message: any) => void;
  lastMessage: WebSocketMessage | null;
  readyState: number;
  connecting: boolean;
  connected: boolean;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [readyState, setReadyState] = useState<number>(WebSocket.CONNECTING);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const maxReconnectAttempts = options.reconnectAttempts || 10;
  const reconnectInterval = options.reconnectInterval || 3000;
  const [connectAttempt, setConnectAttempt] = useState<number>(0);

  // Get WebSocket URL
  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/ws`;
  }, []);

  // Function to create a new WebSocket connection
  const connect = useCallback(() => {
    try {
      // Close existing socket if it exists
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }

      // Create new socket
      const wsUrl = getWebSocketUrl();
      console.log(`Connecting to WebSocket at ${wsUrl}`);
      
      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;
      setReadyState(WebSocket.CONNECTING);
      
      // Set up event handlers
      socket.onopen = () => {
        console.log('WebSocket connected successfully');
        setReadyState(WebSocket.OPEN);
        reconnectAttemptsRef.current = 0;
        if (options.onOpen) options.onOpen();
      };

      socket.onmessage = (event) => {
        try {
          console.log('Raw WebSocket message received:', event.data);
          const message = JSON.parse(event.data);
          console.log('Parsed WebSocket message:', message);
          setLastMessage(message);
          if (options.onMessage) options.onMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      socket.onclose = (event) => {
        console.log('WebSocket disconnected with code:', event.code);
        setReadyState(WebSocket.CLOSED);
        
        if (options.onClose) options.onClose();
        
        // Try to reconnect if not intentionally closed
        if (!event.wasClean && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          console.log(`Attempting to reconnect (${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`);
          
          if (reconnectTimeoutRef.current !== null) {
            window.clearTimeout(reconnectTimeoutRef.current);
          }
          
          reconnectTimeoutRef.current = window.setTimeout(() => {
            setConnectAttempt(prev => prev + 1); // Trigger a connect attempt
          }, reconnectInterval);
        }
      };

      socket.onerror = (error) => {
        console.error('WebSocket error occurred:', error);
        if (options.onError) options.onError(error);
      };
    } catch (err) {
      console.error('Error creating WebSocket connection:', err);
    }
  }, [getWebSocketUrl, options, maxReconnectAttempts, reconnectInterval]);

  // Send message through WebSocket
  const sendMessage = useCallback((message: any) => {
    try {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        const msgStr = JSON.stringify(message);
        console.log('Sending WebSocket message:', msgStr);
        socketRef.current.send(msgStr);
      } else {
        console.warn('Cannot send message, WebSocket is not open. ReadyState:', 
          socketRef.current ? socketRef.current.readyState : 'null');
      }
    } catch (err) {
      console.error('Error sending WebSocket message:', err);
    }
  }, []);

  // Set up WebSocket connection on mount and clean up on unmount
  useEffect(() => {
    connect();
    
    // Ping to keep connection alive (at a shorter interval)
    const pingInterval = window.setInterval(() => {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        sendMessage({ type: 'ping', timestamp: Date.now() });
      }
    }, 15000); // Ping every 15 seconds
    
    return () => {
      // Clean up on unmount
      if (reconnectTimeoutRef.current !== null) {
        window.clearTimeout(reconnectTimeoutRef.current);
      }
      
      window.clearInterval(pingInterval);
      
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [connect, sendMessage, connectAttempt]); // Added connectAttempt dependency

  return {
    sendMessage,
    lastMessage,
    readyState,
    connecting: readyState === WebSocket.CONNECTING,
    connected: readyState === WebSocket.OPEN,
  };
}