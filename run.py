import os

from github_mock import app
from github_mock.database import create_tables


if __name__ == "__main__":
    print('create tables ...')
    create_tables()
    print('run app ...')
    APP_PORT = os.environ.get('APP_PORT', '5000')
    APP_PORT = int(APP_PORT)
    app.run(debug=True, host='0.0.0.0', port=APP_PORT)
