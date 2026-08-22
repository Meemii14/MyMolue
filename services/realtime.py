from flask_socketio import SocketIO, join_room

socketio = SocketIO(cors_allowed_origins="*")

def init_realtime(app):
    socketio.init_app(app, message_queue=app.config.get("SOCKETIO_MESSAGE_QUEUE") or None)

@socketio.on("join_ride")
def join_ride(data):
    ride_id = data.get("ride_id") if isinstance(data, dict) else None
    if ride_id is not None:
        join_room(f"ride:{ride_id}")
