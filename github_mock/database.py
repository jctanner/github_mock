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


from .constants import DB_NAME
from .constants import UPSTREAM_PROTO
from .constants import UPSTREAM_HOST
from .constants import UPSTREAM_PORT
from .constants import UPSTREAM
from .constants import API_SERVER
from .constants import CLIENT_API_SERVER
from .constants import USERS
from .constants import OAUTH_APPS


def create_tables():

    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()

    for uname, uinfo in USERS.items():
        sql = "INSERT OR IGNORE INTO users (id, login, email, password) VALUES(?, ?, ?, ?)"
        print(sql)
        cursor.execute(sql, (uinfo['id'], uinfo['login'], uinfo['email'], uinfo['password'],))
        conn.commit()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT NOT NULL PRIMARY KEY,
            uid TEXT NOT NULL
        )
    ''')
    conn.commit()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_tokens (
            access_token TEXT NOT NULL PRIMARY KEY,
            uid TEXT NOT NULL
        )
    ''')
    conn.commit()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS csrf_tokens (
            csrf_token TEXT NOT NULL PRIMARY KEY,
            uid TEXT NOT NULL
        )
    ''')
    conn.commit()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS oauth_apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            uid TEXT NOT NULL,
            homepage TEXT NOT NULL,
            callback TEXT NOT NULL,
            clientid TEXT NOT NULL,
            secretid TEXT NOT NULL
        )
    ''')
    conn.commit()

    for oapp in OAUTH_APPS:
        sql = 'INSERT OR IGNORE INTO oauth_apps'
        sql += ' (name, uid, homepage, callback, clientid, secretid)'
        sql += ' VALUES(?, ?, ?, ?, ?, ?)'
        print(sql)
        cursor.execute(
            sql,
            (oapp['name'], oapp['uid'], oapp['homepage'], oapp['callback'], oapp['clientid'], oapp['secretid'],)
        )
        conn.commit()

    conn.close()


def get_user_by_id(userid):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id,login,email,password FROM users WHERE id = ?', (userid,))
    row = cursor.fetchone()
    userid = row[0]
    login = row[1]
    email = row[2]
    password = row[3]
    conn.close()
    return {'id': userid, 'login': login, 'email': email, 'password': password}


def get_user_by_login(login):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    print(f'FINDING USER BY LOGIN:{login}')
    cursor.execute('SELECT id,login,email,password FROM users WHERE login = ?', (login,))
    row = cursor.fetchone()
    if row is None:
        return None
    userid = row[0]
    login = row[1]
    email = row[2]
    password = row[3]
    conn.close()
    return {'id': userid, 'login': login, 'email': email, 'password': password}


def get_session_by_id(sid):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT id,uid FROM sessions WHERE id = ?', (sid,))
    row = cursor.fetchone()
    rsid = row[0]
    userid = row[1]
    conn.close()
    return {'session': rsid, 'uid': userid}


def set_session(sid, uid):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT into sessions (id, uid) VALUES (?, ?)',
        (sid, uid)
    )
    conn.commit()
    conn.close()


def make_session(username):
    user = get_user_by_login(username)
    sessionid = str(uuid.uuid4())
    set_session(sessionid, user['id'])
    return sessionid


def get_access_token_by_id(sid):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT access_token,uid FROM access_tokens WHERE access_token = ?', (sid,))
    row = cursor.fetchone()
    rsid = row[0]
    userid = row[1]
    conn.close()
    return {'access_token': rsid, 'uid': userid}


def set_access_token(token, uid):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT into access_tokens (access_token, uid) VALUES (?, ?)',
        (token, uid)
    )
    conn.commit()
    conn.close()


def delete_access_token(token):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM access_tokens WHERE access_token=?',
        (token,)
    )
    conn.commit()
    conn.close()


def get_csrf_token_by_id(sid):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT csrf_token,uid FROM access_tokens WHERE csrf_token = ?', (sid,))
    row = cursor.fetchone()
    rsid = row[0]
    userid = row[1]
    conn.close()
    return {'csrf_token': rsid, 'uid': userid}


def set_csrf_token(token, uid):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT into csrf_tokens (id, uid) VALUES (?, ?)',
        (token, uid)
    )
    conn.commit()
    conn.close()


def get_new_uid():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(id) FROM users')
    highest_id = cursor.fetchone()[0]
    conn.close()
    return highest_id + 1


def get_new_login():
    return ''.join([random.choice(string.ascii_lowercase) for x in range(0, 5)])


def get_new_password():
    return ''.join([random.choice(string.ascii_lowercase) for x in range(0, 12)])


def get_user_list():
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

    return users


def get_oauth_app_list():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    '''
        id TEXT NOT NULL PRIMARY KEY,
            name TEXT NOT NULL,
            uid TEXT NOT NULL,
            homepage TEXT NOT NULL,
            callback TEXT NOT NULL,
            clientid TEXT NOT NULL,
            secretid TEXT NOT NULL
    '''

    sql = "SELECT id, uid, name, homepage, callback, clientid, secretid FROM oauth_apps"
    cursor.execute(sql)
    rows = cursor.fetchall()

    apps = []
    for row in rows:
        appid = row[0]
        uid = row[1]
        udata = get_user_by_id(uid)

        name = row[2]
        homepage = row[3]
        callback = row[4]
        clientid = row[5]
        secretid = row[6]

        u = {
            'id': appid,
            'uid': uid,
            'name': name,
            'login': udata['login'],
            'homepage': homepage,
            'callback': callback,
            'clientid': clientid,
            'secretid': secretid
        }

        apps.append(u)

    conn.close()

    return apps


def get_oauth_app_by_client_id(client_id):
    oauth_apps = get_oauth_app_list()
    oapps = [x for x in oauth_apps if x['clientid'] == client_id]
    return oapps[0]


def check_username_and_password(username, password):

    try:
        user = get_user_by_login(username)
    except:
        print(f'{username} not found')
        return False

    if user.get('password') != password:
        print(f'{password} bad password')

    if user.get('password') == password:
        return True

    return False


def alter_user_data(src_data, new_data):

    new_userid = new_data.get('id')
    if not new_userid:
        new_userid = src_data['id']
    new_login = new_data.get('login')
    new_email = new_data.get('email')
    new_password = new_data.get('password')

    # must delete to change the uid
    delete = False
    if new_userid is not None and new_userid != src_data['id']:
        delete = True

    if new_login is None:
        new_login = udata['id']
    if new_login is None:
        new_login = udata['login']
    if new_email is None:
        new_email = udata['email']
    if new_password is None:
        new_password = udata['password']

    if delete:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id=?', (src_data['id'],))
        conn.commit()
        cursor.execute(
            'INSERT INTO users (id, login, email, password) VALUES (?,?,?,?)',
            (new_userid, new_login, new_email, new_password,)
        )
        conn.commit()
        conn.close()

    else:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET login=?, email=?, password=? WHERE id=?',
            (new_login, new_email, new_password, src_data['id'],)
        )
        conn.commit()
        conn.close()

    return get_user_by_id(new_userid)


def delete_user(id=None, login=None):
    cursor = conn.cursor()

    if id:
        sql = 'DELETE FROM users WHERE id=?'
        cursor.execute(sql, (id,))
        conn.commit()

    if login:
        sql = 'DELETE FROM users WHERE login=?'
        cursor.execute(sql, (login,))
        conn.commit()

    conn.close()


def add_user(ds):
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

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print(f'CREATING USER {login} with {password}')
    sql = "INSERT OR IGNORE INTO users (id, login, email, password) VALUES(?, ?, ?, ?)"
    print(sql)
    cursor.execute(sql, (userid, login, email, password,))
    conn.commit()

    conn.close()
    return {'id': userid, 'login': login, 'email': email, 'password': password}


def create_oauth_app(
    login=None,
    name=None,
    homepage=None,
    callback=None,
    clientid=None,
    secretid=None
):

    # get the UID for the login ...
    udata = get_user_by_login(login)
    userid = udata['id']

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    sql = """
        INSERT OR IGNORE INTO oauth_apps (
            uid, name, homepage, callback, clientid, secretid
        ) VALUES(
            ?, ?, ?, ?, ?, ?
        )
    """
    print(sql)
    cursor.execute(sql, (userid, name, homepage, callback, clientid, secretid,))

    conn.commit()
    conn.close()
