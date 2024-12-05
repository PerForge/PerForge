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

from app                                       import app
from app.backend.components.secrets.secrets_db import DBSecrets
from app.backend.errors                        import ErrorMessages
from app.forms                                 import SecretForm
from flask                                     import render_template, request, url_for, redirect, flash
from flask_login                               import current_user


@app.route('/secrets', methods=['get'])
def get_secrets():
    try:
        project_id = request.cookies.get('project')
        secrets    = DBSecrets.get_configs(id=project_id)
        return render_template('home/secrets.html', secrets=secrets)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00051.value, "error")
        return redirect(url_for("index"))

@app.route('/add_secret', methods=['GET', 'POST'])
def add_secret():
    try:
        form = SecretForm(request.form)
        if form.validate_on_submit():
            try:
                project_id                = request.cookies.get('project')
                secret_data               = form.data
                secret_data['project_id'] = project_id if secret_data['project_id'] == "project" else None
                secret_data['type']       = "admin" if current_user.is_admin else "general"

                for key, value in secret_data.items():
                    if value == '':
                        secret_data[key] = None

                if DBSecrets.get_config_by_key(key=secret_data['key']):
                    flash("Secret with this key already exists.", "error")
                else:
                    DBSecrets.save(data = secret_data)
                    flash("Secret added.", "info")
                return redirect(url_for('get_secrets'))
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.ER00049.value, "error")
                return redirect(url_for('get_secrets'))
        return render_template('home/secret.html', form=form)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00051.value, "error")
        return redirect(url_for('get_secrets'))

@app.route('/edit_secret', methods=['GET'])
def edit_secret():
    try:
        secret_id   = request.args.get('secret_id')
        secret_type = request.args.get('secret_type')

        if not secret_id or not secret_type:
            flash("Secret ID and type are required.", "error")
            return redirect(url_for('get_secrets'))

        if secret_type == "admin" and not current_user.is_admin:
            flash("You do not have permission to access this page.", "error")
            return redirect(url_for('get_secrets'))

        output = DBSecrets.get_config_by_id(id=secret_id)
        form   = SecretForm(data=output)
        return render_template('home/secret.html', form=form, secret_id=secret_id, secret_type=secret_type)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00051.value, "error")
        return redirect(url_for('get_secrets'))

@app.route('/update_secret', methods=['POST'])
def update_secret():
    try:
        form       = SecretForm(request.form)
        if form.validate_on_submit():
            try:
                project_id                = request.cookies.get('project')
                secret_data               = form.data
                secret_data['project_id'] = project_id if secret_data['project_id'] == "project" else None
                secret_data['type']       = "admin" if current_user.is_admin else "general"

                for key, value in secret_data.items():
                    if value == '':
                        secret_data[key] = None

                if DBSecrets.get_config_by_key(key=secret_data['key']):
                    flash("Secret with this key already exists.", "error")
                else:
                    DBSecrets.update(data=secret_data)
                    flash("Secret updated.", "info")
                return redirect(url_for('get_secrets'))
            except Exception:
                logging.warning(str(traceback.format_exc()))
                flash(ErrorMessages.ER00049.value, "error")
                return redirect(url_for('get_secrets'))
        return render_template('home/secret.html', form=form, secret_id=secret_id, secret_type=secret_type)
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00051.value, "error")
        return redirect(url_for('get_secrets'))

@app.route('/delete/secret', methods=['GET'])
def delete_secret():
    try:
        secret_id   = request.args.get('secret_id')
        secret_type = request.args.get('secret_type')

        if not secret_id or not secret_type:
            flash("Secret ID and type are required.", "error")
            return redirect(url_for('get_secrets'))

        if secret_type == "admin" and not current_user.is_admin:
            flash("You do not have permission to access this page.", "error")
            return redirect(url_for('get_secrets'))

        DBSecrets.delete(id=secret_id)
        flash("Secret deleted.", "info")
    except Exception:
        logging.warning(str(traceback.format_exc()))
        flash(ErrorMessages.ER00050.value, "error")
    return redirect(url_for('get_secrets'))
