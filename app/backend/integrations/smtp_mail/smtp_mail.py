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

from app                                                 import app
from app.backend.integrations.integration                import Integration
from app.backend.integrations.smtp_mail.smtp_mail_config import SmtpMailConfig
from flask                                               import render_template
from flask_mail                                          import Mail, Message
from os                                                  import path


class SmtpMail(Integration):

    def __init__(self, project, id = None):
        super().__init__(project)
        self.set_config(id)

    def __str__(self):
        return f'Integration id is {self.id}, url is {self.org_url}'

    def set_config(self, id):
        if path.isfile(self.config_path) is False or os.path.getsize(self.config_path) == 0:
            logging.warning("There is no config file.")
        else:
            id     = id if id else SmtpMailConfig.get_default_smtp_mail_config_id(self.project)
            config = SmtpMailConfig.get_smtp_mail_config_values(self.project, id, is_internal=True)
            if "id" in config:
                if config['id'] == id:
                    self.id         = config["id"]
                    self.name       = config["name"]
                    self.server     = self.remove_trailing_slash(config["server"])
                    self.port       = config["port"]
                    self.use_ssl    = config["use_ssl"]
                    self.use_tls    = config["use_tls"]
                    self.username   = config["username"]
                    self.password   = config["token"]
                    self.recipients = [value for key, value in config.items() if key.startswith("recipients-")]
                else:
                    return {"status":"error", "message":"No such config name"}

    def put_page_to_mail(self, subject, report_body, report_images):
        mail_settings = {
            'MAIL_SERVER'  : self.server,
            'MAIL_PORT'    : self.port,
            'MAIL_USE_SSL' : eval(self.use_ssl),
            'MAIL_USE_TLS' : eval(self.use_tls),
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