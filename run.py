from github_mock import app
from github_mock.database import create_tables


if __name__ == "__main__":
    print('create tables ...')
    create_tables()
    print('run app ...')
    app.run(debug=True, host='0.0.0.0', port=5000)
