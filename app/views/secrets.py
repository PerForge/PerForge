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

from app                          import app
from app.backend.database.secrets import DBSecrets
from app.forms                    import SecretForm
from app.backend.errors           import ErrorMessages
from flask                        import render_template, request, url_for, redirect, flash
from flask_login                  import current_user


@app.route('/secrets', methods=['get'])
def get_secrets():
    try:
        project_id = request.cookies.get('project')
        secrets    = DBSecrets.get_configs(project_id)
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
                project_id   = request.cookies.get('project')
                secret       = request.form.to_dict()
                secret_key   = secret.get("key")
                secret_value = secret.get("value")
                scope        = secret.get("project_id")

                secret_type = "admin" if current_user.is_admin else "general"
                secret_project_id = project_id if scope == "project" else None

                new_secret  = DBSecrets(
                    key=secret_key,
                    type=secret_type,
                    value=secret_value,
                    project_id=secret_project_id
                )
                new_secret.save()
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
        project_id = request.cookies.get('project')
        form       = SecretForm(request.form)
        secret_id  = request.args.get('secret_id')
        if form.validate_on_submit():
            try:
                secret_data  = request.form.to_dict()
                secret_id    = secret_data.get("id")
                secret_key   = secret_data.get("key")
                secret_type  = secret_data.get("type")
                secret_value = secret_data.get("value")
                scope        = secret_data.get("project_id")

                secret_project_id = project_id if scope == "project" else None
                if secret_type == "None":
                    if current_user.is_admin:
                        secret_type = "admin"
                    else:
                        secret_type = "general"

                DBSecrets.update(id=secret_id, key=secret_key, type=secret_type, value=secret_value, project_id=secret_project_id)
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