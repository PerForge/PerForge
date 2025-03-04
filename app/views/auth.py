# Copyright 2024 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import traceback
import logging

from app                                         import app, login_manager, bc, db
from app.backend                                 import pkg
from app.backend.components.users.users_db       import DBUsers
from app.backend.components.projects.projects_db import DBProjects
from app.backend.errors                          import ErrorMessages
from app.forms                                   import LoginForm, RegisterForm
from flask                                       import g, render_template, request, url_for, redirect, flash
from flask_login                                 import login_user, logout_user, current_user
from jinja2                                      import TemplateNotFound
from functools                                   import wraps


# List of routes that do not require authentication
no_auth_required_routes = ['login', 'register', 'static','register_admin', 'generate', 'generate_report','delete-influxdata','gen-report']
need_admin_routes = ['static','register_admin']

class User:
    def __init__(self, user_data):
        self.user_data = user_data

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_admin(self):
        return bool(self.user_data.get('is_admin', False))

    def get_id(self):
        return str(self.user_data.get('id'))

@app.before_request
def check_authentication():
    g.user = current_user
    if not DBUsers.check_admin_exists():
        if request.endpoint not in need_admin_routes:  # Exclude register_admin from redirect
            return redirect(url_for('register_admin'))
    elif not g.user.is_authenticated and request.endpoint not in no_auth_required_routes:
        return redirect(url_for('login'))

# provide login manager with load_user callback
@login_manager.user_loader
def load_user(user_id):
    config = DBUsers.get_config_by_id(user_id)
    if config:
        return User(config)
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.user_data.get('is_admin'):
            flash("You do not have permission to access this page.", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Logout user
@app.route('/logout')
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for('index'))

# Register a new user
@app.route('/register', methods=['GET', 'POST'])
@admin_required
def register():
    try:
        # declare the Registration Form
        form = RegisterForm(request.form)
        if request.method == 'GET':
            return render_template( 'accounts/register.html', form=form)
        # check if both http method is POST and form is valid on submit
        if form.validate_on_submit():
            user_data = form.data
            # filter User out of database through username
            if DBUsers.get_config_by_username(user=user_data['user']):
                flash("User exists!", "info")
            else:
                user_data['id'] = None
                user_data['password'] = bc.generate_password_hash(user_data['password']).decode('utf-8')
                user_data['is_admin'] = False
                DBUsers.save(data=user_data)
                return redirect(url_for('login')), flash("User created", "info")
        else:
            flash("Input error.", "info")
        return render_template('accounts/register.html', form=form)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00022.value, "error")
        return redirect(url_for('register'))

# Register a new admin
@app.route('/register-admin', methods=['GET', 'POST'])
def register_admin():
    try:
        if DBUsers.check_admin_exists():
            flash("You do not have permission to access this page.", "error")
            return redirect(url_for('index'))
        # declare the Registration Form
        form    = RegisterForm(request.form)
        if request.method == 'GET':
            return render_template( 'accounts/register.html', form=form, admin=True)
        # check if both http method is POST and form is valid on submit
        if form.validate_on_submit():
            user_data = form.data
            user_data['id'] = None
            user_data['password'] = bc.generate_password_hash(user_data['password']).decode('utf-8')
            user_data['is_admin'] = True
            DBUsers.save(data=user_data)
            return redirect(url_for('login')), flash("Admin user created", "info")
        else:
            flash("Input error.", "info")
        return render_template('accounts/register.html', form=form, admin=True)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00022.value, "error")
        return redirect(url_for('register'))

# Authenticate user
@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if current_user.is_authenticated:
            return redirect(url_for('choose_project'))

        form = LoginForm(request.form)
        if form.validate_on_submit():
            username = request.form['user']
            password = request.form['password']
            user = DBUsers.get_config_by_username(user=username)
            if user:
                if bc.check_password_hash(user['password'], password):
                    login_user(User(user))
                    return redirect(url_for('choose_project'))
                else:
                    flash("Wrong password. Please try again.", "info")
            else:
                flash("Unknown user.", "info")
        admin = getattr(current_user, 'user_data', {}).get('is_admin', False)
        return render_template('accounts/login.html', form=form, admin=admin)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00023.value, "error")
        return redirect(url_for('login'))

# App main route + generic routing
@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path>')
def index(path):
    try:
        project = request.cookies.get('project')
        if project != None:
            # Close and reset database connections to ensure schema changes take effect
            db.session.close()
            db.engine.dispose()
            
            # Force a complete reset of all SQLAlchemy connections
            with app.app_context():
                projects = DBProjects.get_configs()
                project_stats = DBProjects.get_project_stats(project)
                current_version = pkg.get_current_version_from_file()
            
            return render_template('home/' + path, projects=projects, project_stats=project_stats, current_version=current_version)
        else:
            return redirect(url_for('choose_project'))
    except TemplateNotFound:
        return render_template('home/page-404.html'), 404
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00024.value, "error")
        return render_template('home/page-500.html'), 500
