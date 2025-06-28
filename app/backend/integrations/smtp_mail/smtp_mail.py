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

import os
import logging

from app                                             import app
from app.backend.integrations.integration            import Integration
from app.backend.integrations.smtp_mail.smtp_mail_db import DBSMTPMail
from app.backend.components.secrets.secrets_db       import DBSecrets
from flask                                           import render_template
from flask_mail                                      import Mail, Message


class SmtpMail(Integration):

    def __init__(self, project, id = None):
        super().__init__(project)
        self.set_config(id)

    def __str__(self):
        return f'Integration id is {self.id}, url is {self.org_url}'

    def set_config(self, id):
        id     = id if id else DBSMTPMail.get_default_config(project_id=self.project)["id"]
        config = DBSMTPMail.get_config_by_id(project_id=self.project, id=id)
        if config['id']:
            self.id         = config["id"]
            self.name       = config["name"]
            self.server     = config["server"]
            self.port       = config["port"]
            self.use_ssl    = config["use_ssl"]
            self.use_tls    = config["use_tls"]
            self.username   = config["username"]
            self.password   = DBSecrets.get_config_by_id(project_id=self.project, id=config["token"])["value"]
            self.recipients = [recipient['email'] for recipient in config.get('recipients', [])]
        else:
            logging.warning("There's no SMTP Mail integration configured, or you're attempting to send a request from an unsupported location.")

    def put_page_to_mail(self, subject, report_body, report_images):
        mail_settings = {
            'MAIL_SERVER'  : self.server,
            'MAIL_PORT'    : self.port,
            'MAIL_USE_SSL' : str(self.use_ssl).lower() in ('true', '1', 't'),
            'MAIL_USE_TLS' : str(self.use_tls).lower() in ('true', '1', 't'),
            'MAIL_USERNAME': self.username,
            'MAIL_PASSWORD': self.password,
        }
        app.config.update(mail_settings)
        mail = Mail(app)
        try:
            html = render_template('integrations/mail-report.html', body = report_body)
            msg  = Message(
                subject    = subject,
                sender     = self.username,
                recipients = self.recipients,
                html       = html
            )
            for img in report_images:
                msg.attach(filename = img["file_name"], content_type = 'image/png', data = img["data"], headers = [['Content-ID', img["content_id"]]])

            logo_file_path = os.path.join('app', 'static', 'assets', 'img', 'logo.png')
            with open(logo_file_path, 'rb') as f:
                logo_data = f.read()
            msg.attach(filename = 'logo.png', content_type = 'image/png', data = logo_data, headers = [['Content-ID', 'perforge_logo']])

            output = mail.send(msg)
            return output
        except Exception as er:
            logging.warning(er)
            return {"status":"error", "message":er}
