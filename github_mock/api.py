#!/usr/bin/env python

###############################################################################
#
#   local github social auth mock
#
#       Implements just enough of github.com to supply what is needed for api
#       tests to do github social auth (no browser).
#
###############################################################################


import os
import uuid
import random
import string
import sqlite3
# import requests

from flask import Flask
from flask import jsonify
from flask import request
from flask import redirect
from flask import make_response
from flask import session


# app = Flask(__name__)
from github_mock import app

from .constants import DB_NAME
from .constants import UPSTREAM_PROTO
from .constants import UPSTREAM_HOST
from .constants import UPSTREAM_PORT
from .constants import UPSTREAM
from .constants import API_SERVER
from .constants import CLIENT_API_SERVER
from .constants import USERS

from .database import create_tables
from .database import get_user_by_id
from .database import get_user_by_login
from .database import get_session_by_id
from .database import set_session
from .database import get_access_token_by_id
from .database import set_access_token
from .database import delete_access_token
from .database import get_csrf_token_by_id
from .database import set_csrf_token
from .database import get_new_uid
from .database import get_new_login
from .database import get_new_password


@app.route('/user', methods=['GET', 'POST'])
def github_user():
 
    # The token in the headers should allow correlation with the user this returns data about ...
    auth = request.headers['Authorization']
    print(auth)
    token = auth.split()[-1].strip()
    print(f'TOKEN: {token}')

    # fetch the token to get the uid associated
    token_data = get_access_token_by_id(token)

    # get the user via the uid
    _udata = get_user_by_id(token_data['uid'])
    username = _udata['login']
    print(username)

    # make it a one time token?
    delete_access_token(token)

    # fetch the full info about the user and drop the password
    udata = get_user_by_login(username)
    udata.pop('password', None)
    print(udata)

    return jsonify(udata)
