from app import create_app
from flask_session import Session

app = create_app()
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 