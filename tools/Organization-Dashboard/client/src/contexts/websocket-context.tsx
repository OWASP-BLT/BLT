import React, { createContext, useContext, useCallback, useState, useEffect, useRef } from 'react';
import { useWebSocket, WebSocketMessage } from '@/hooks/use-websocket';
import { queryClient } from '@/lib/queryClient';

// Define the shape of our context
interface WebSocketContextType {
  lastMessage: WebSocketMessage | null;
  connected: boolean;
  connecting: boolean;
  sendMessage: (message: any) => void;
}

// Create the context with a default value
const WebSocketContext = createContext<WebSocketContextType>({
  lastMessage: null,
  connected: false,
  connecting: false,
  sendMessage: () => {},
});

// Export the Provider component
export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [notifications, setNotifications] = useState<WebSocketMessage[]>([]);

  // Send message function will be needed in the handleMessage callback
  const sendMessageRef = useRef<(message: any) => void>(() => {
    console.warn('WebSocket not initialized yet');
  });

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((message: WebSocketMessage) => {
    console.log('WebSocket message received:', message);

    // Handle different message types
    switch (message.type) {
      case 'dashboard_stats':
      case 'dashboard_stats_updated':
        // Invalidate dashboard stats queries
        queryClient.invalidateQueries({ queryKey: ['/api/dashboard/stats'] });
        break;

      case 'new_bug_report':
        // Invalidate bug reports queries
        queryClient.invalidateQueries({ queryKey: ['/api/bugs'] });
        break;

      case 'new_security_issue':
        // Invalidate security issues queries
        queryClient.invalidateQueries({ queryKey: ['/api/security-issues'] });
        break;

      case 'new_activity':
        // Invalidate activity logs queries
        queryClient.invalidateQueries({ queryKey: ['/api/activity'] });
        
        // Add to notifications
        setNotifications(prev => [message, ...prev.slice(0, 9)]);
        break;

      case 'recent_activities':
        // Initial activities load
        break;

      case 'simple_stats':
        // Simple stats message from server
        console.log('Received simple stats from server:', message.data);
        break;

      case 'ping':
        // Respond with pong to keep connection alive
        console.log('Received ping from server, responding with pong');
        try {
          // Log more details about the ping message
          console.log('Ping message details:', message);
          
          // Try both ways to send the pong response
          sendMessageRef.current({ type: 'pong', timestamp: Date.now() });
          
          // Don't break the connection on ping
          return; // Skip the break to prevent any disconnection logic
        } catch (err) {
          console.error('Error sending pong response:', err);
        }
        break;

      case 'pong':
        // Pong response from server (keep-alive)
        console.log('Received pong from server');
        break;

      default:
        console.log('Unknown message type:', message.type);
    }
  }, [queryClient]);

  // Create WebSocket connection
  const { sendMessage, lastMessage, connected, connecting } = useWebSocket({
    onMessage: handleMessage,
    onOpen: () => console.log('WebSocket connected'),
    onClose: () => console.log('WebSocket disconnected'),
    onError: (error) => console.error('WebSocket error:', error),
    reconnectInterval: 3000,
    reconnectAttempts: 10,
  });

  // Update the ref value whenever sendMessage changes
  useEffect(() => {
    sendMessageRef.current = sendMessage;
  }, [sendMessage]);

  // Provide the WebSocket context to all children
  return (
    <WebSocketContext.Provider
      value={{
        lastMessage,
        connected,
        connecting,
        sendMessage,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
};

// Export a hook for using the WebSocket context
export const useWebSocketContext = () => useContext(WebSocketContext);