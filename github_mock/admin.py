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



@app.route('/admin/users/list', methods=['GET'])
def admin_user_list():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    sql = "SELECT id, login, email, password FROM users"
    cursor.execute(sql)
    rows = cursor.fetchall()

    users = []
    for row in rows:
        userid = row[0]
        login = row[1]
        email = row[2]
        password = row[3]
        u = {'id': userid, 'login': login, 'email': email, 'password': password}
        users.append(u)

    conn.close()

    return jsonify(users)


@app.route('/admin/users/add', methods=['POST'])
def admin_add_user():
    ds = request.json

    userid = ds.get('id', get_new_uid())
    if userid is None:
        userid = get_new_uid()
    else:
        userid = int(userid)
    login = ds.get('login', get_new_login())
    if login is None:
        login = get_new_login()
    password = ds.get('password', get_new_password())
    if password is None:
        password = get_new_password()
    email = ds.get('email', login + '@github.com')
    # if email is None or not email:
    #    email = login + '@github.com'

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print(f'CREATING USER {login} with {password}')
    sql = "INSERT OR IGNORE INTO users (id, login, email, password) VALUES(?, ?, ?, ?)"
    print(sql)
    cursor.execute(sql, (userid, login, email, password,))
    conn.commit()

    conn.close()
    return jsonify({'id': userid, 'login': login, 'email': email, 'password': password})


@app.route('/admin/users/remove', methods=['DELETE'])
def admin_remove_user():
    ds = request.json

    userid = ds.get('id', get_new_uid())
    if userid is None:
        userid = get_new_uid()
    login = ds.get('login', get_new_login())
    if login is None:
        login = get_new_login()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if userid:
        sql = 'DELETE FROM users WHERE id=?'
        cursor.execute(sql, (userid,))
        conn.commit()
    if login:
        sql = 'DELETE FROM users WHERE login=?'
        cursor.execute(sql, (login,))
        conn.commit()

    conn.close()
    return jsonify({'status': 'complete'})


@app.route('/admin/users/byid/<int:userid>', methods=['GET', 'POST'])
@app.route('/admin/users/bylogin/<string:login>', methods=['GET', 'POST'])
def admin_modify_user(userid=None, login=None):

    if request.method == 'GET':
        if userid:
            udata = get_user_by_id(userid)
        elif login:
            udata = get_user_by_login(login)
        return jsonify(udata)

    print(request.data)

    ds = request.json
    new_userid = ds.get('id')
    new_login = ds.get('login')
    new_password = ds.get('password')

    udata = None
    if userid is not None:
        udata = get_user_by_id(userid)
    elif login is not None:
        udata = get_user_by_login(login)

    print(udata)

    # must delete to change the uid
    delete = False
    if new_userid is not None and new_userid != udata['id']:
        delete = True

    if new_login is None:
        new_login = udata['id']
    if new_login is None:
        new_login = udata['login']
    if new_password is None:
        new_password = udata['password']

    if delete:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user WHERE id=?', (udata['id'],))
        conn.commit()
        cursor.execute(
            'INSERT INTO users (id, login, password) VALUES (?,?,?)',
            (new_userid, new_login, new_password,)
        )
        conn.commit()
        conn.close()

    else:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET login=?, password=? WHERE id=?',
            (new_login, new_password, udata['id'],)
        )
        conn.commit()
        conn.close()

    udata = get_user_by_login(new_login)
    return jsonify(udata)
