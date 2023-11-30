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
from urllib.parse import urlencode
# import requests

from flask import Flask
from flask import jsonify
from flask import request
from flask import redirect
from flask import make_response
from flask import session
from flask import render_template


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
from .database import get_oauth_app_by_client_id


# https://www.bigbinary.com/blog/how-to-use-jwt-to-secure-your-github-oauth-callback-endpoint
# client_id - 
#	This is an ID used by GitHub for identifying the application. You
#	need to register your application with GitHub to get this ID.
# redirect_uri -
#	The URI to which GitHub should send back a request once the
#	authorization is approved.
# login -
#	This is a username on GitHub. The application requires access to data on
#	behalf of the user with this username.
# state -
#	This should ideally be a string of random characters. Store this string
#	in memory because it will be used in another step. This parameter is optional 
#   but highly recommended. We'll look into why later.

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

    # We need to know if this is a logged in user ... so do they have a _gh_sess and is it valid?
    login = None
    uid = None
    _gh_sess = request.cookies.get('_gh_sess')
    session_data = None
    if _gh_sess:
        try:
            session_data = get_session_by_id(_gh_sess)
            uid = session_data['uid']
            udata = get_user_by_id(uid)
            login = udata['login']
        except Exception as e:
            pass

    # if not logged in, they need to login first ... THEN get back to the authorize page
    #if '_gh_sess' not in request.cookies:
    if login is None:
        # craft the redirect url
        url = '/ui/login'

        # set the return_to parameter
        return_to = urlencode(dict(request.args))
        url += '?' + urlencode({'return_to': '/login/oauth/authorize?' + return_to})
        print(f'LOGIN REDIRECT: {url}')

        # make a redirect response
        resp = make_response(redirect(url))

        # set the _gh_sess cookie (for anonymous user)
        sessionid = str(uuid.uuid4())
        resp.set_cookie('_gh_sess', sessionid)

        # return response
        return resp

    # now they need to see the authorize page ...
    if request.method == 'GET':

        # Need to associate this integration to an oauth-app so we can get ...
        client_id = request.args.get('client_id')
        oauth_app = get_oauth_app_by_client_id(client_id)

        kwargs = {
            'username': login,
            'app_name': oauth_app['name'],
            'app_owner': oauth_app['login'],
            'client_id': client_id,
            'callback': oauth_app['callback'],
            'redirect_url': oauth_app['homepage']
        }
        return render_template('oauth_authorize.html', **kwargs)

    # POST ...
    '''
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
    '''

    url = f'{CLIENT_API_SERVER}/complete/github/'
    token = str(uuid.uuid4())
    set_access_token(token, uid)
    url += f'?code={token}&state=null'
    resp = redirect(url, code=302)
    return resp


@app.route('/login/oauth/access_token', methods=['GET', 'POST'])
def do_access_token():

    ds = request.json
    print(f'AT ds: {ds}')

    '''
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
    '''

    '''
    print(f'SESSION: {session}')
    login = session.get('login')
    print(f'LOGIN: {login}')
    resp.set_cookie('_gh_sess', sessionid)
    resp.set_cookie('_user_session', sessionid)
    '''

    # the user must be identified by the _gh_sess cookie
    # which matches the session ID and is tied to a UID in the db

    print(f'COOKIES: {request.cookies}')
    _gh_sess = request.cookies.get('_gh_sess')
    print(f'_GH_SESS: {_gh_sess}')
    gh_session = get_session_by_id(_gh_sess)
    print(f'GH_SESSION: {gh_session}')

    token = str(uuid.uuid4())

    return jsonify({
        'access_token': token
    })


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
    new_session = get_session_by_id(sessionid)
    print(f'NEW SESSION: {new_session}')
    # SESSION_IDS[sessionid] = username

    redirect_uri = request.args.get('redirect_uri', '/')
    print(f'REDIRECT TO {redirect_uri} ...')

    resp = make_response(redirect(redirect_uri))
    #resp = make_response(redirect('http://localhost:8002/'))
    resp.set_cookie('_gh_sess', sessionid)
    resp.set_cookie('_user_session', sessionid)
    resp.set_cookie('dotcom_user', username)
    resp.set_cookie('logged_in', 'yes')

    session['username'] = username

    return resp
