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

import logging

from app import app
from flask import render_template, request, url_for, redirect, flash
from flask_login import current_user


@app.route('/secrets', methods=['GET'])
def get_secrets():
    """
    Render the secrets list page.
    The actual data is loaded via API client on the frontend.
    """
    try:
        return render_template('home/secrets.html')
    except Exception as e:
        logging.error(f"Error rendering secrets page: {str(e)}")
        flash("An error occurred while loading the secrets page.", "error")
        return redirect(url_for("index"))


@app.route('/add_secret', methods=['GET'])
def add_secret():
    try:
        return render_template('home/secret.html')
    except Exception as e:
        logging.error(f"Error rendering add secret page: {str(e)}")
        flash("An error occurred while loading the add secret page.", "error")
        return redirect(url_for('get_secrets'))


@app.route('/edit_secret', methods=['GET'])
def edit_secret():
    try:
        secret_id = request.args.get('secret_id')

        if not secret_id:
            flash("Secret ID is required.", "error")
            return redirect(url_for('get_secrets'))

        return render_template('home/secret.html')
    except Exception as e:
        logging.error(f"Error rendering edit secret page: {str(e)}")
        flash("An error occurred while loading the edit secret page.", "error")
        return redirect(url_for('get_secrets'))
