import { io } from 'socket.io-client';
export class SocketService {

  //api = new ApiService()

  // Creates socket connection to server.
  createSocket(endpoint, room = null) {
    // Start on long-polling and upgrade to WebSocket only if the server
    // supports it. The app used to force websocket-only, but the eventlet->
    // threading server migration broke the WebSocket transport, so a
    // websocket-only client could never connect (live updates silently died).
    // Polling always works; if WS is restored later, engine.io auto-upgrades.
    const socket = io(window.location.protocol + '//' + window.location.host + '/' + endpoint, {transports: ['polling', 'websocket']});
    socket.on('connect', e => {
      if (room != null) {
        socket.emit('join_room', {room: room});
      }
    });
    
    socket.on('disconnect', e => {});
    socket.on('connecting', e => {});
    socket.on('connect_failed', e => {});
    socket.on('connect_error', e => {});
    socket.on('error', e => {});
    socket.on('reconnect', e => {});
    socket.on('reconnecting', e => {});
    socket.on('reconnect_error', e => {});
    socket.on('reconnect_failed', e => { });
    return socket;
  }
}
