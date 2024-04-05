#!/usr/bin/env python

import atexit
import copy
import datetime
import glob
import json
import docker
import os
import psycopg
import time

from logzero import logger

import os
import uuid
import random
import string
import sqlite3


from github_mock.constants import (
    DB_NAME,
    UPSTREAM_PROTO,
    UPSTREAM_HOST,
    UPSTREAM_PORT,
    UPSTREAM,
    API_SERVER,
    CLIENT_API_SERVER,
    USERS,
    OAUTH_APPS
)



USERS_SCHEMA = '''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        login TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL,
        password TEXT NOT NULL
    )
'''


SESSIONS_SCHEMA = '''
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT NOT NULL PRIMARY KEY,
        uid TEXT NOT NULL
    )
'''


ACCESS_TOKENS_SCHEMA = '''
    CREATE TABLE IF NOT EXISTS access_tokens (
        access_token TEXT NOT NULL PRIMARY KEY,
        uid TEXT NOT NULL
    )
'''

CSRF_TOKENS_SCHEMA = '''
    CREATE TABLE IF NOT EXISTS csrf_tokens (
        csrf_token TEXT NOT NULL PRIMARY KEY,
        uid TEXT NOT NULL
    )
'''

OAUTH_APPS_SCHEMA = '''
    CREATE TABLE IF NOT EXISTS oauth_apps (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        uid TEXT NOT NULL,
        homepage TEXT NOT NULL,
        callback TEXT NOT NULL,
        clientid TEXT NOT NULL,
        secretid TEXT NOT NULL
    )
'''

class GithubDatabaseWrapper:

    IMAGE = 'postgres'
    NAME = 'github_database'
    USER = 'github'
    PASS = 'github'
    DB = 'github'
    IP = None
    _conn = None
    spawn_db_container = True

    def __init__(self):

        self.spawn_db_container = os.environ.get('SPAWN_DB_CONTAINER')
        if self.spawn_db_container is None:
            self.spawn_db_container = True
        elif self.spawn_db_container in ['false', 'False', 'FALSE', '0']:
            self.spawn_db_container = False
        elif self.spawn_db_container in ['true', 'True', 'TRUE', '1']:
            self.spawn_db_container = True

        if self.spawn_db_container:
            self.get_ip()
        else:
            self.IP = os.environ.get('POSTGRES_HOST', 'postgres')
            self.DB = os.environ.get('POSTGRES_DB', 'github')
            self.USER = os.environ.get('POSTGRES_USER', 'github')
            self.PASS = os.environ.get('POSTGRES_PASSWORD', 'github')

            self.wait_for_connection()

    def start_database(self, clean=False):

        if not self.spawn_db_container:
            return

        client = docker.APIClient()

        for container in client.containers(all=True):
            name = container['Names'][0].lstrip('/')
            if name == self.NAME:

                if container['State'] == 'running' and not clean:
                    self.get_ip()
                    return

                if container['State'] != 'running' and not clean:
                    client.start(self.NAME)
                    self.get_ip()
                    return

                if container['State'] != 'exited':
                    logger.info(f'kill {self.NAME}')
                    client.kill(self.NAME)
                logger.info(f'remove {self.NAME}')
                client.remove_container(self.NAME)

        logger.info(f'pull {self.IMAGE}')
        client.pull(self.IMAGE)
        logger.info(f'create {self.NAME}')
        container = client.create_container(
            self.IMAGE,
            name=self.NAME,
            environment={
                'POSTGRES_DB': self.DB,
                'POSTGRES_USER': self.USER,
                'POSTGRES_PASSWORD': self.PASS,
            }
        )
        logger.info(f'start {self.NAME}')
        client.start(self.NAME)

        # enumerate the ip address ...
        self.get_ip()

        logger.info('wait for connection ...')
        while True:
            try:
                self.get_connection()
                break
            except Exception:
                pass

    def wait_for_connection(self):

        counter = 0
        while True:
            counter += 1
            if counter >= 20:
                raise Exception('failed to connect to datbase')

            logger.info(f'{counter}: testing database connection ...')
            try:
                self.get_connection()
                break
            except Exception:
                time.sleep(1)

    def get_ip(self):

        if not self.spawn_db_container:
            return

        client = docker.APIClient()
        for container in client.containers(all=True):
            name = container['Names'][0].lstrip('/')
            if name == self.NAME:
                self.IP = container['NetworkSettings']['Networks']['bridge']['IPAddress']
                logger.info(f'container IP {self.IP}')
                break
        return self.IP

    def get_connection(self):
        connstring = f'host={self.IP} dbname={self.DB} user={self.USER} password={self.PASS}'
        return psycopg.connect(connstring)

    def check_table_and_create(self, tablename):
        conn = self.get_connection()
        with conn.cursor() as cur:
            cur.execute("select * from information_schema.tables where table_name=%s", (tablename,))
            exists = bool(cur.rowcount)
            if not exists:
                if tablename == 'jira_issue_events':
                    cur.execute(ISSUE_EVENT_SCHEMA)
            conn.commit()

    def load_database(self):
        try:
            conn = self.get_connection()

            # create schema ...
            with conn.cursor() as cur:
                print('CALL USERS_SCHEMA')
                cur.execute(USERS_SCHEMA)
                print('CALL SESSIONS_SCHEMA')
                cur.execute(SESSIONS_SCHEMA)
                print('CALL ACCESS_TOKENS_SCHEMA')
                cur.execute(ACCESS_TOKENS_SCHEMA)
                print('CALL OAUTH_APPS_SCHEMA')
                cur.execute(OAUTH_APPS_SCHEMA)
                conn.commit()
        except Exception as e:
            logger.exception(e)

    @property
    def conn(self):
        if self._conn is None:
            self._conn = self.get_connection()
            atexit.register(self._conn.close)
        return self._conn

    # ABSTRACTIONS ...


def create_tables():

    logger.info('create wrapper')
    gdbw = GithubDatabaseWrapper()
    logger.info('start database')
    gdbw.start_database(clean=True)
    logger.info('load database')
    gdbw.load_database()

    conn = gdbw.conn

    with conn.cursor() as cur:
        for uname, uinfo in USERS.items():
            sql = "INSERT INTO users (id, login, email, password) VALUES(%s, %s, %s, %s)"
            print(sql)
            try:
                cur.execute(sql, (uinfo['id'], uinfo['login'], uinfo['email'], uinfo['password'],))
                conn.commit()
            except psycopg.errors.UniqueViolation:
                conn.rollback()

    with conn.cursor() as cur:
        for oapp in OAUTH_APPS:
            sql = 'INSERT INTO oauth_apps'
            sql += ' (name, uid, homepage, callback, clientid, secretid)'
            sql += ' VALUES(%s, %s, %s, %s, %s, %s)'
            print(sql)
            try:
                cur.execute(
                    sql,
                    (
                        oapp['name'],
                        oapp['uid'],
                        oapp['homepage'],
                        oapp['callback'],
                        oapp['clientid'],
                        oapp['secretid'],
                    )
                )
                conn.commit()
            except psycopg.errors.UniqueViolation:
                conn.rollback()


    conn.close()


def get_user_by_id(userid):

    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn

    cursor = conn.cursor()
    cursor.execute('SELECT id,login,email,password FROM users WHERE id = %s', (userid,))
    row = cursor.fetchone()
    userid = row[0]
    login = row[1]
    email = row[2]
    password = row[3]
    conn.close()
    return {'id': userid, 'login': login, 'email': email, 'password': password}


def get_user_by_login(login):

    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn

    cursor = conn.cursor()
    print(f'FINDING USER BY LOGIN:{login}')
    cursor.execute('SELECT id,login,email,password FROM users WHERE login = %s', (login,))
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

    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn

    cursor = conn.cursor()
    cursor.execute('SELECT id,uid FROM sessions WHERE id = %s', (sid,))
    row = cursor.fetchone()
    rsid = row[0]
    userid = row[1]
    conn.close()
    return {'session': rsid, 'uid': userid}


def set_session(sid, uid):

    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn

    cursor = conn.cursor()
    cursor.execute(
        'INSERT into sessions (id, uid) VALUES (%s, %s)',
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

    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn

    cursor = conn.cursor()
    cursor.execute('SELECT access_token,uid FROM access_tokens WHERE access_token = %s', (sid,))
    row = cursor.fetchone()
    rsid = row[0]
    userid = row[1]
    conn.close()
    return {'access_token': rsid, 'uid': userid}


def set_access_token(token, uid):

    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn

    cursor = conn.cursor()
    cursor.execute(
        'INSERT into access_tokens (access_token, uid) VALUES (%s, %s)',
        (token, uid)
    )
    conn.commit()
    conn.close()


def delete_access_token(token):

    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn

    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM access_tokens WHERE access_token=%s',
        (token,)
    )
    conn.commit()
    conn.close()


def get_csrf_token_by_id(sid):

    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn

    cursor = conn.cursor()
    cursor.execute('SELECT csrf_token,uid FROM access_tokens WHERE csrf_token = %s', (sid,))
    row = cursor.fetchone()
    rsid = row[0]
    userid = row[1]
    conn.close()
    return {'csrf_token': rsid, 'uid': userid}


def set_csrf_token(token, uid):

    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn

    cursor = conn.cursor()
    cursor.execute(
        'INSERT into csrf_tokens (id, uid) VALUES (%s, %s)',
        (token, uid)
    )
    conn.commit()
    conn.close()


def get_new_uid():

    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn

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

    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn

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

    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn

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

        print('KNOWN USERS ...')
        users = get_user_list()
        for _user in users:
            print(f'\t{_user}')

        return False

    print(f'CHECK FOUND {user}')

    if user is None:
        print('KNOWN USERS ...')
        users = get_user_list()
        for _user in users:
            print(f'\t{_user}')

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

        gdbw = GithubDatabaseWrapper()
        conn = gdbw.conn

        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id=%s', (src_data['id'],))
        conn.commit()
        cursor.execute(
            'INSERT INTO users (id, login, email, password) VALUES (%s,%s,%s,%s)',
            (new_userid, new_login, new_email, new_password,)
        )
        conn.commit()
        conn.close()

    else:

        gdbw = GithubDatabaseWrapper()
        conn = gdbw.conn

        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET login=%s, email=%s, password=%s WHERE id=%s',
            (new_login, new_email, new_password, src_data['id'],)
        )
        conn.commit()
        conn.close()

    return get_user_by_id(new_userid)


def delete_user(id=None, login=None):

    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn

    cursor = conn.cursor()

    if id:
        sql = 'DELETE FROM users WHERE id=%s'
        cursor.execute(sql, (id,))
        conn.commit()

    if login:
        sql = 'DELETE FROM users WHERE login=%s'
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

    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn
    cursor = conn.cursor()

    print(f'CREATING USER {login} with {password}')
    sql = "INSERT INTO users (id, login, email, password) VALUES(%s, %s, %s, %s)"
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

    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn
    cursor = conn.cursor()

    sql = """
        INSERT INTO oauth_apps (
            uid, name, homepage, callback, clientid, secretid
        ) VALUES(
            %s, %s, %s, %s, %s, %s
        )
    """
    print(sql)
    cursor.execute(sql, (userid, name, homepage, callback, clientid, secretid,))

    conn.commit()
    conn.close()


def delete_oauth_app(appid=None):
    gdbw = GithubDatabaseWrapper()
    conn = gdbw.conn
    cursor = conn.cursor()

    sql = """
        DELETE FROM oauth_apps WHERE id=%s
    """
    print(sql)
    cursor.execute(sql, (appid,))

    conn.commit()
    conn.close()


def main():

    '''
    logger.info('create wrapper')
    gdbw = GithubDatabaseWrapper()
    logger.info('start database')
    gdbw.start_database(clean=True)
    logger.info('load database')
    gdbw.load_database()
    '''
    create_tables()


if __name__ == "__main__":
    main()

