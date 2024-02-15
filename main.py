from app import app, socketio
from app.config import Config

if __name__ == '__main__':
    # app.run(debug=True)
    
    if Config.TESTING:
        # For local run
        socketio.run(app, debug=True, host='0.0.0.0', port=5000, log_output=True)
    
    else:
        # For GCP
        socketio.run(app, debug=True, host='0.0.0.0', port=8080, log_output=True, allow_unsafe_werkzeug=True)
    
