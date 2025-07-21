# Copyright 2025 Uladzislau Shklianik <ushklianik@gmail.com> & Siamion Viatoshkin <sema.cod@gmail.com>
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
import uuid
import traceback
import time
from typing import Optional
from lxml import etree
from app.backend.integrations.integration                                  import Integration
from app.backend.integrations.atlassian_confluence.atlassian_confluence_db import DBAtlassianConfluence
from app.backend.components.secrets.secrets_db                             import DBSecrets
from atlassian                                                             import Confluence


class AtlassianConfluence(Integration):

    def __init__(self, project, id = None):
        super().__init__(project)
        self.set_config(id)

    def __str__(self):
        return f'Integration id is {self.id}, url is {self.org_url}'

    def set_config(self, id):
        id     = id if id else DBAtlassianConfluence.get_default_config(project_id=self.project)["id"]
        config = DBAtlassianConfluence.get_config_by_id(project_id=self.project, id=id)
        if config['id']:
            self.id        = config["id"]
            self.name      = config["name"]
            self.email     = config["email"]
            self.token     = DBSecrets.get_config_by_id(project_id=self.project, id=config["token"])["value"]
            self.org_url   = config["org_url"]
            self.space_key = config["space_key"]
            self.parent_id = config["parent_id"]
            if config["token_type"] == "api_token":
                self.confluence_auth = Confluence(
                    url      = self.org_url,
                    username = self.email,
                    password = self.token
                )
            else:
                self.confluence_auth = Confluence(
                    url   = self.org_url,
                    token = self.token
                )
        else:
            logging.warning("There's no Confluence integration configured, or you're attempting to send a request from an unsupported location.")

    def put_page(self, title, content):
        """Create a new Confluence page or update it if it already exists.

        The Atlassian REST API returns an error when a page with the same
        title already exists within the same parent.  In this situation we
        interpret the error as an *expected* condition and simply update the
        existing page instead of treating it as a failure.
        """
        try:
            # Try to create a brand-new page first.
            return self.confluence_auth.create_page(
                space=self.space_key,
                title=title,
                body=content,
                parent_id=self.parent_id,
            )
        except Exception as er:
            err_msg = str(er).lower()

            # Confluence responds with messages like
            # "A page with this title already exists" when the title clashes.
            if "already exists" in err_msg and "title" in err_msg:
                # Retrieve existing page id and perform an update instead.
                try:
                    page_id = self.confluence_auth.get_page_id(self.space_key, title)
                    if page_id:
                        return self.update_page(page_id=page_id, title=title, content=content)
                    # If for some reason the page id cannot be found, fall
                    # through to logging so the user can take action.
                except Exception as update_error:
                    logging.warning(f"Failed to update existing Confluence page '{title}': {update_error}")
                    logging.debug(traceback.format_exc())
                    return None

            # Any other exception is unexpected – log it as before.
            logging.warning(f"An error occurred while creating Confluence page '{title}': {er}")
            logging.debug(traceback.format_exc())
            return None

    def put_image_to_confl(self, image, name, page_id):
        name = f'{uuid.uuid4()}.png'
        for _ in range(3):
            try:
                self.confluence_auth.attach_content(content=image, name=name, content_type="image/png", page_id=page_id, space=self.space_key)
                return name
            except Exception as er:
                logging.warning('ERROR: uploading image to confluence failed')
                logging.warning(er)
            time.sleep(10)

    def update_page(self, page_id, title, content):
        """Update a Confluence page, fixing XHTML if possible before sending."""

        sanitized = self._sanitize_xhtml(content)
        if sanitized is None:
            msg = f"XHTML content is invalid and could not be auto-corrected; aborting Confluence page update for page '{title}'."
            logging.warning(msg)
            return {"status": "error", "message": msg}

        try:
            response = self.confluence_auth.update_page(page_id=page_id, title=title, body=sanitized)
            return response
        except Exception as er:
            logging.warning(er)
            return {"status":"error", "message":er}

    # ------------------------------------------------------------------
    # XHTML helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_xhtml(content: str) -> Optional[str]:
        """Return a well-formed XHTML fragment or *None* if it cannot be fixed.

        Strategy:
        1. Attempt *strict* parsing (recover=False). If valid, return original.
        2. Otherwise parse with *recover=True* which tells *lxml* to try to
           repair common issues (unclosed tags, illegal nesting, etc.).  The
           repaired tree is then serialised back to an XHTML string.
        3. If recovery also fails, return *None*.
        """
        if not content:
            return None

        wrapper = f"<div>{content}</div>"

        # First try strict validation.
        try:
            etree.fromstring(wrapper, etree.XMLParser(recover=False, resolve_entities=False, no_network=True))
            return content  # already valid
        except etree.XMLSyntaxError:
            pass  # will try to recover below

        # Attempt to recover/fix the markup.
        try:
            tree = etree.fromstring(wrapper, etree.XMLParser(recover=True, resolve_entities=False, no_network=True))
            # Serialise children of the wrapper div back to string
            fixed_parts = [etree.tostring(child, encoding='unicode', method='xml') for child in tree]
            fixed_content = ''.join(fixed_parts)

            # Double-check the repaired output is now valid.
            etree.fromstring(f"<div>{fixed_content}</div>", etree.XMLParser(recover=False, resolve_entities=False, no_network=True))
            logging.info("XHTML content was auto-corrected before update.")
            return fixed_content
        except etree.XMLSyntaxError as exc:
            logging.warning(f"XHTML recovery failed: {exc}")
            return None
