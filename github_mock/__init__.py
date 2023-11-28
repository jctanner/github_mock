from flask import Flask

app = Flask(__name__)
app.secret_key = 'REDHAT1234'

from github_mock import api
from github_mock import ux
from github_mock import admin
from github_mock import oauth
