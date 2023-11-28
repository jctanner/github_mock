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



# ----------------------------------------------------
# Github authorization redirect sequence ...
# /login/oauth/authorize -> /login -> /session -> /login/oauth/authorize

# Backend response sequence ...
# /complete/github/?code=9257c509396232aa4f67 -> /accounts/profile



@app.route('/login/oauth/authorize', methods=['GET', 'POST'])
def do_authorization():
    """
    The client is directed here first from the galaxy UI to allow oauth
    """

    print(f'COOKIES: {request.cookies}')

    if '_gh_sess' not in request.cookies:
        print(request.args)
        kwargs = {}
        for k,v in request.args.items():
            kwargs[k] = v
        print(kwargs)
        query_string = '&'.join([f"{key}={value}" for key, value in kwargs.items()])
        return redirect('/ui/login' + '?' + query_string)

    # Verify the user is authenticated?
    _gh_sess = request.cookies['_gh_sess']
    print(f'_GH_SESS: {_gh_sess}')
    # assert _gh_sess in SESSION_IDS
    # username = SESSION_IDS[_gh_sess]


    try:
        this_session = get_session_by_id(_gh_sess)
    except Exception as e:
        print('failed getting session')
        print(e)
        sessionid = str(uuid.uuid4())
        login = session.get('login')
        udata = get_user_by_login(login)
        uid = udata['id']
        print(f'make new session for uid:{uid}')
        set_session(sessionid, uid)
        this_session = get_session_by_id(sessionid)
        print(f'new session: {this_session}')

    assert this_session

    username = get_user_by_id(this_session['uid'])
    assert username

    # Tell the backend to complete the login for the user ...
    # url = f'{API_SERVER}/complete/github/'
    url = f'{CLIENT_API_SERVER}/complete/github/'
    token = str(uuid.uuid4())
    # ACCESS_TOKENS[token] = username
    set_access_token(token, this_session['uid'])
    url += f'?code={token}'

    # FIXME
    print(f'REDIRECT_URL: {url}')
    resp = redirect(url, code=302)
    return resp


@app.route('/login/oauth/access_token', methods=['GET', 'POST'])
def do_access_token():
    ds = request.json
    access_code = ds['code']
    # client_id = ds['client_id']
    # client_secret = ds['client_secret']

    # Match the acces_code to the username and invalidate it
    # username = ACCESS_TOKENS[access_code]
    _at = get_access_token_by_id(access_code)
    udata = get_user_by_id(_at['uid'])
    # ACCESS_TOKENS.pop(access_code, None)
    delete_access_token(access_code)

    # Make a new token
    token = str(uuid.uuid4())
    # ACCESS_TOKENS[token] = username
    set_access_token(token, udata['id'])

    return jsonify({'access_token': token})


# The github login page will post form data here ...
@app.route('/session', methods=['POST'])
def do_session():

    """
    if request.method == 'GET':
        resp = jsonify({})
        csrftoken = str(uuid.uuid4())
        CSRF_TOKENS[csrftoken] = None
        resp.set_cookie('csrftoken', csrftoken)
        return resp
    """

    # form data ...
    #   username
    #   password

    username = request.form.get('username')
    password = request.form.get('password')
    print(f'DO_SESSION username:{username} password:{password}')
    udata = get_user_by_login(username)

    assert udata is not None, f'{username}:{password}'
    assert udata['password'] == password

    sessionid = str(uuid.uuid4())
    set_session(sessionid, udata['id'])
    # SESSION_IDS[sessionid] = username

    resp = make_response(redirect('/'))
    #resp = make_response(redirect('http://localhost:8002/'))
    resp.set_cookie('_gh_sess', sessionid)
    resp.set_cookie('_user_session', sessionid)
    resp.set_cookie('dotcom_user', username)
    resp.set_cookie('logged_in', 'yes')

    session['username'] = username

    return resp
