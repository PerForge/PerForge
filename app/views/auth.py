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

from app                import app, login_manager, bc
from app.backend        import pkg
from app.models         import Users
from app.forms          import LoginForm, RegisterForm
from app.backend.errors import ErrorMessages
from flask              import g, render_template, request, url_for, redirect, flash
from flask_login        import login_user, logout_user, current_user
from jinja2             import TemplateNotFound
from functools          import wraps


# List of routes that do not require authentication
no_auth_required_routes = ['login', 'register', 'static','register_admin', 'generate', 'generate_report','delete-influxdata','gen-report']
need_admin_routes = ['static','register_admin']

@app.before_request
def check_authentication():
    g.user = current_user
    if not Users.check_admin_exists():
        if request.endpoint not in need_admin_routes:  # Exclude register_admin from redirect
            return redirect(url_for('register_admin'))
    elif not g.user.is_authenticated and request.endpoint not in no_auth_required_routes:
        return redirect(url_for('login'))

# provide login manager with load_user callback
@login_manager.user_loader
def load_user(user_id):
    return Users.query.filter(Users.id == int(user_id)).first()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
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
            # assign form data to variables
            username = request.form.get('username', '', type=str)
            password = request.form.get('password', '', type=str)
            # filter User out of database through username
            user = Users.query.filter_by(user=username).first()
            # filter User out of database through username
            if user :
                flash("User exists!", "info")
            else:
                pw_hash = bc.generate_password_hash(password)
                user    = Users(username, pw_hash)
                user.save()
                return redirect(url_for('login')), flash("User created", "info")
        else:
            flash("Input error.", "info")
        return render_template('accounts/register.html', form=form)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.REGISTER.value, "error")
        return redirect(url_for('register'))

# Register a new admin
@app.route('/register-admin', methods=['GET', 'POST'])
def register_admin():
    try:
        if Users.check_admin_exists():
            flash("You do not have permission to access this page.", "error")
            return redirect(url_for('index'))
        # declare the Registration Form
        form    = RegisterForm(request.form)
        if request.method == 'GET':
            return render_template( 'accounts/register.html', form=form, admin=True)
        # check if both http method is POST and form is valid on submit
        if form.validate_on_submit():
            # assign form data to variables
            username = request.form.get('username', '', type=str)
            password = request.form.get('password', '', type=str)
            # filter User out of database through username
            user = Users.query.filter_by(user=username).first()
            # filter User out of database through username
            pw_hash = bc.generate_password_hash(password)
            user    = Users(username, pw_hash, is_admin=True)
            user.save()
            return redirect(url_for('login')), flash("Admin user created", "info")
        else:
            flash("Input error.", "info")
        return render_template('accounts/register.html', form=form, admin=True)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.REGISTER.value, "error")
        return redirect(url_for('register'))

# Authenticate user
@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        # Declare the login form
        form = LoginForm(request.form)
        # check if both http method is POST and form is valid on submit
        if form.validate_on_submit():
            # assign form data to variables
            username = request.form.get('username', '', type=str)
            password = request.form.get('password', '', type=str)
            # filter User out of database through username
            user = Users.query.filter_by(user=username).first()
            if user:
                if bc.check_password_hash(user.password, password):
                    login_user(user)
                    return redirect(url_for('choose_project'))
                else:
                    flash("Wrong password. Please try again.", "info")
            else:
                flash("Unknown user.", "info")
        admin = getattr(current_user, 'is_admin', False)
        return render_template('accounts/login.html', form=form, admin=admin)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.LOGIN.value, "error")
        return redirect(url_for('login'))

# App main route + generic routing
@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path>')
def index(path):
    try:
        project = request.cookies.get('project')
        if project != None:
            projects        = pkg.get_all_projects()
            project_stats   = pkg.get_project_config_stats(project)
            current_version = pkg.get_current_version_from_file()
            return render_template('home/' + path, projects = projects, project_stats=project_stats, current_version=current_version)
        else:
            return redirect(url_for('choose_project'))
    except TemplateNotFound:
        return render_template('home/page-404.html'), 404
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.OOPS_MSG.value, "error")
        return render_template('home/page-500.html'), 500