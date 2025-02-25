import { useState,useEffect } from 'react';
import { logout } from './auth'; // For handling auth-related disconnects

export class WebSocketClient {
  constructor({
    url,
    onMessage,
    onOpen = () => console.log('WebSocket connected'),
    onClose = () => console.log('WebSocket closed'),
    onError = (error) => console.error('WebSocket error:', error),
    reconnectInterval = 1000, // Initial reconnect delay in ms
    maxReconnectAttempts = 5, // Maximum reconnect attempts
    authToken = localStorage.getItem('token'), // Optional JWT token
  }) {
    this.url = url;
    this.onMessage = onMessage;
    this.onOpen = onOpen;
    this.onClose = onClose;
    this.onError = onError;
    this.reconnectInterval = reconnectInterval;
    this.maxReconnectAttempts = maxReconnectAttempts;
    this.authToken = authToken;

    this.ws = null;
    this.reconnectAttempts = 0;
    this.isConnected = false;
    this.isClosing = false;

    this.connect();
  }

  // Establish WebSocket connection
  connect() {
    if (this.isClosing) return;

    // Append token to URL if provided (or use headers if supported by backend)
    const wsUrl = this.authToken ? `${this.url}?token=${this.authToken}` : this.url;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.isConnected = true;
      this.reconnectAttempts = 0;
      this.onOpen();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.onMessage(data);
      } catch (error) {
        this.onError(new Error(`Failed to parse WebSocket message: ${error.message}`));
      }
    };

    this.ws.onclose = (event) => {
      this.isConnected = false;
      if (!this.isClosing) {
        this.onClose(event);
        this.reconnect();
      }
    };

    this.ws.onerror = (error) => {
      this.isConnected = false;
      this.onError(error);
      // Reconnection is handled by onclose
    };
  }

  // Reconnect with exponential backoff
  reconnect() {
    if (this.isClosing || this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.onError(new Error('Max reconnect attempts reached or connection intentionally closed'));
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        logout(); // Logout if persistent failure (e.g., token expired)
        if (typeof window !== "undefined") {
          window.location.href = '/login';
        }
      }
      return;
    }

    const delay = Math.min(
      this.reconnectInterval * Math.pow(2, this.reconnectAttempts),
      30000 // Cap at 30 seconds
    );
    console.log(`Reconnecting in ${delay / 1000} seconds... (Attempt ${this.reconnectAttempts + 1})`);
    setTimeout(() => {
      this.reconnectAttempts += 1;
      this.connect();
    }, delay);
  }

  // Send a message to the WebSocket server
  send(data) {
    if (!this.isConnected || !this.ws) {
      console.warn('WebSocket is not connected; message dropped:', data);
      return false;
    }

    try {
      const message = typeof data === 'string' ? data : JSON.stringify(data);
      this.ws.send(message);
      return true;
    } catch (error) {
      this.onError(new Error(`Failed to send WebSocket message: ${error.message}`));
      return false;
    }
  }

  // Close the WebSocket connection
  close() {
    if (this.ws) {
      this.isClosing = true;
      this.ws.close();
      this.isConnected = false;
      this.reconnectAttempts = 0; // Reset attempts on intentional close
    }
  }

  // Get connection status
  getStatus() {
    return {
      isConnected: this.isConnected,
      reconnectAttempts: this.reconnectAttempts,
      url: this.url,
    };
  }
}

// Hook for easier WebSocket usage in React components
export function useWebSocket({
  url,
  onMessage,
  onOpen,
  onClose,
  onError,
  reconnectInterval = 1000,
  maxReconnectAttempts = 5,
  enabled = true, // Toggle WebSocket connection
}) {
  const [client, setClient] = useState(null);

  useEffect(() => {
    if (!enabled || !url) return;

    const wsClient = new WebSocketClient({
      url,
      onMessage,
      onOpen,
      onClose,
      onError,
      reconnectInterval,
      maxReconnectAttempts,
    });

    setClient(wsClient);

    return () => {
      wsClient.close();
      setClient(null);
    };
  }, [url, enabled, reconnectInterval, maxReconnectAttempts]); // Dependencies simplified

  return {
    client,
    send: (data) => client?.send(data),
    status: client?.getStatus() || { isConnected: false, reconnectAttempts: 0, url },
  };
}

// Example usage
if (require.main === module) {
  const testWs = new WebSocketClient({
    url: 'ws://localhost:8000/ws',
    onMessage: (data) => console.log('Received:', data),
    onOpen: () => console.log('Connected'),
    onClose: () => console.log('Disconnected'),
    onError: (err) => console.error('Error:', err),
  });

  setTimeout(() => testWs.send({ event: 'test', data: 'Hello' }), 2000);
  setTimeout(() => testWs.close(), 5000);
}

export default WebSocketClient;