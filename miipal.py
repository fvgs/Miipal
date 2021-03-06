"""
User refers to the person affiliated with a particular name in the network.
Client refers to the client-end of a connection.
    e.g. Each tab in Chrome is considered a client.
"""

from flask import Flask, render_template, request
from flask.ext.socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.debug = True
socketio = SocketIO(app)

# Maps client session ids to names
clients = {}
# Maps names to number of clients using that name
# e.g. if user is connecting from multiple tabs
users = {}

@app.route('/')
def home():
    """Render the home page."""
    return render_template('home.html')

@socketio.on('join')
def on_join(data):
    """Respond to the 'join' event by registering the user.

    Create a client entry for the joining user, add the client to the room
    representing the given user, and broadcast the user's joining to all
    connected clients."""

    try:
        name = data['name']
    except KeyError:
        return

    # Name must not be empty
    if not name:
        return

    clients[request.namespace.socket.sessid] = name
    users[name] = users.get(name, 0) + 1
    
    # Add client to the room representing the user
    join_room(name)

    # If user was not already connected
    if users[name] == 1:
        # Broadcast the user that just joined
        emit('add user', {'user': name}, broadcast=True)

@socketio.on('get users')
def on_get_users():
    """Respond to the 'get users' event with the list of connected users."""
    user_names = users.keys()
    # If client has already joined the server
    if clients.has_key(request.namespace.socket.sessid):
        # Remove the client's name from the list of users
        user_names.remove(clients[request.namespace.socket.sessid])

    emit('update users', {'user_list': user_names})

@socketio.on('send message')
def on_send_message(data):
    """Respond to the 'send message' event by routing the message.

    Verify that the sending user has joined, and proceed to broadcast the
    message to all clients connected to the room corresponding to the
    recipient."""

    try:
        sender = data['sender']
        recipient = data['recipient']
        message = data['message']
    except KeyError:
        return

    # Sender has not joined the server
    if not request.namespace.socket.sessid in clients:
        return

    data = {
        'sender': sender,
        'message': message,
    }
    emit('new message', data, room=recipient)

@socketio.on('disconnect')
def on_disconnect():
    """Remove disconnected client and broadcast to connected users."""
    # If client did not join server prior to disconnecting
    if not clients.get(request.namespace.socket.sessid):
        return

    # Get the user associated with this client connection
    user = clients[request.namespace.socket.sessid]
    # Remove client from list of client connections
    del clients[request.namespace.socket.sessid]

    # If this is the last connection for this user
    if users.get(user, 1) <= 1:
        # Delete from list of users
        del users[user]
        # Broadcast departure of this user
        emit('remove user', {'user': user}, broadcast=True)
    # Otherwise decrease count by one
    else:
        users[user] = users[user] - 1

if __name__ == '__main__':
    socketio.run(app, heartbeat_interval=.5)