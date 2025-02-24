export class WebSocketClient {
  constructor(url, onMessage) {
    this.url = url;
    this.onMessage = onMessage;
    this.connect();
  }

  connect() {
    this.ws = new WebSocket(this.url);
    this.ws.onmessage = (event) => this.onMessage(JSON.parse(event.data));
    this.ws.onclose = () => this.reconnect();
    this.ws.onerror = (error) => console.error('WebSocket error:', error);
  }

  reconnect() {
    setTimeout(() => this.connect(), 1000);
  }

  close() {
    this.ws.close();
  }
}
