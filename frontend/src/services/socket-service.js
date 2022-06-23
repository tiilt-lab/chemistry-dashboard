import * as SocketIO from  'socket.io-client';

export class SocketService {

  //api = new ApiService()

  // Creates socket connection to server.
  createSocket(endpoint, room = null) {
    const socket = SocketIO.connect(window.location.protocol + '//' + window.location.hostname + '/' + endpoint);
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
