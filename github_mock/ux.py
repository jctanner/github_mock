from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    make_response,
)

from github_mock import app
from .database import get_user_list
from .database import check_username_and_password
from .database import make_session
from .database import get_user_by_id
from .database import alter_user_data
from .database import delete_user
from .database import get_oauth_app_list
from .database import add_user
from .database import create_oauth_app


@app.route('/')
def root():
    return redirect('/ui')


@app.route('/ui')
def ui_root():
    return render_template('index.html')


@app.route('/ui/login', methods=['GET', 'POST'])
def ui_login():
    if request.method == 'POST':
        # Here, add logic to verify username and password

        username = request.form['username']
        password = request.form['password']

        if check_username_and_password(username, password):
            print('login success, redirect to root')

            #sid = make_session(username)
            #print(f'sid {sid}')
            session['username'] = username

            print(session)
            print(request.args)

            redirect_uri = request.args.get('redirect_uri')
            client_id = request.args.get('client_id')
            response_type = request.args.get('response_type')

            print(f'REDIRECT_URI: {redirect_uri}')
            if redirect_uri:
                return redirect(redirect_uri)
            #return redirect(url_for('root'))

            resp = make_response(redirect(url_for('root')))
            resp.set_cookie('_gh_sess', 'some_cookie_value')
            return resp

        else:
            print('flashing')
            flash('Invalid credentials')

    return render_template('login.html')


@app.route('/ui/logout')
def ui_logout():
    session.pop('username', None)
    flash('You were successfully logged out')
    return redirect(url_for('ui_root'))


@app.route('/ui/users/', methods=['GET', 'POST'])
def ui_users():

    if request.method == 'POST':
        ds = request.json
        print(f'NEW USER DATA: {ds}')
        try:
            add_user(ds)
        except Exception as e:
            return str(e), 599

    return render_template('users.html', users=get_user_list())


@app.route('/ui/users/<int:id>/remove')
def ui_user_delete(id=None):
    try:
        delete_user(id=id)
    except Exception as e:
        return str(e), 500

    return render_template('users.html', users=get_user_list())


@app.route('/ui/users/<int:id>/edit', methods=['GET', 'POST'])
def ui_user_edit(id=None):

    print(f'INPUT ID: {id}')

    src_data = get_user_by_id(id)
    print(f'old_data: {src_data}')

    user_data = request.json
    print(f'new_data: {user_data}')

    try:
        alter_user_data(src_data, user_data)
    except Exception as e:
        return str(e), 500

    return render_template('users.html', users=get_user_list())


@app.route('/ui/repositories')
def ui_repositories():
    return render_template('repositories.html')


@app.route('/ui/oauth-apps', methods=['GET', 'POST'])
def ui_oauth_apps():
    if request.method == 'POST':
        ds = request.json
        print(f'NEW APP DATA: {ds}')

        try:
            create_oauth_app(**ds)
        except Exception as e:
            return str(e), 500


    return render_template('oauth_apps.html', oauth_apps=get_oauth_app_list())
