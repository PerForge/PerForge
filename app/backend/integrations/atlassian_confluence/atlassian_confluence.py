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
                # Confluence Cloud with API Token
                self.confluence_auth = Confluence(
                    url      = self.org_url,
                    username = self.email,
                    password = self.token,
                    cloud    = True  # Optional but explicit
                )
            else:
                # Confluence Data Center/Server with Personal Access Token
                self.confluence_auth = Confluence(
                    url   = self.org_url,
                    token = self.token,
                    cloud = False  # REQUIRED for PAT on Data Center/Server
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
            response = self.confluence_auth.create_page(
                space=self.space_key,
                title=title,
                body=content,
                parent_id=self.parent_id,
            )
            # Normalise to a simple dict with id key for downstream code.
            page_id = response.get("id") if isinstance(response, dict) else response
            return {"id": page_id}
        except Exception as er:
            # On failure, attempt to find an existing page with the same title
            try:
                page_id = self.confluence_auth.get_page_id(self.space_key, title)
                if page_id:
                    return {"id": page_id}
            except Exception as fetch_error:
                logging.warning(f"Failed to retrieve existing Confluence page id for '{title}': {fetch_error}")
                logging.debug(traceback.format_exc())
                # fall through to generic logging below

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

        # Will raise ValueError if sanitization fails
        sanitized = self._sanitize_xhtml(content)

        try:
            return self.confluence_auth.update_page(page_id=page_id, title=title, body=sanitized)
        except Exception as er:
            logging.warning(er)
            raise RuntimeError(f"Confluence API update_page failed: {er}")

    # ------------------------------------------------------------------
    # XHTML helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_markdown_lists_to_html(content: str) -> str:
        """Convert markdown-style bullet points to HTML lists.

        Converts lines starting with '- ' to proper <ul> and <li> tags.
        This ensures AI-generated bullet lists render correctly in Confluence.

        Args:
            content: Text that may contain markdown bullet points

        Returns:
            Content with markdown lists converted to HTML
        """
        import re
        if not content:
            return content

        # CRITICAL FIX: Split lines where HTML tags are followed immediately by bullet points
        # This handles cases like "</ac:image><br/>- The bullet text"
        # The regex finds any closing tag (>) followed by optional whitespace and "- "
        # and inserts newlines to separate them
        content = re.sub(r'(>)(\s*)- ', r'\1\n\n- ', content)

        lines = content.split('\n')
        result = []
        in_list = False

        for line in lines:
            stripped = line.strip()
            # Check if this is a bullet point (starts with '- ')
            if stripped.startswith('- '):
                if not in_list:
                    result.append('<ul>')
                    in_list = True
                # Remove the '- ' prefix and wrap in <li>
                list_item = stripped[2:].strip()
                result.append(f'<li>{list_item}</li>')
            else:
                # Not a bullet point
                if in_list:
                    result.append('</ul>')
                    in_list = False
                # Always add non-bullet lines (preserves empty lines and HTML)
                result.append(line)

        # Close list if we ended while still in one
        if in_list:
            result.append('</ul>')

        return '\n'.join(result)

    @staticmethod
    def _sanitize_xhtml(content: str) -> Optional[str]:
        """Return a well-formed XHTML fragment or *None* if it cannot be fixed.

        Strategy:
        1. Convert markdown-style lists to HTML lists
        2. Smart newline handling: avoid <br/> around block elements
        3. Attempt *strict* parsing (recover=False). If valid, return original.
        4. Otherwise parse with *recover=True* which tells *lxml* to try to
           repair common issues (unclosed tags, illegal nesting, etc.).  The
           repaired tree is then serialised back to an XHTML string.
        5. If recovery also fails, return *None*.
        """
        if not content:
            raise ValueError("No content provided for XHTML sanitization")

        # First, convert markdown-style bullet points to HTML lists
        content = AtlassianConfluence._convert_markdown_lists_to_html(content)

        # Normalize newlines first
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # Smart newline-to-br conversion: avoid adding <br/> around HTML block elements
        # Block elements that should not have <br/> before or after them
        block_elements = [
            '<ul>', '</ul>', '<ol>', '</ol>', '<li>', '</li>',
            '<h1>', '</h1>', '<h2>', '</h2>', '<h3>', '</h3>', '<h4>', '</h4>', '<h5>', '</h5>', '<h6>', '</h6>',
            '<table>', '</table>', '<thead>', '</thead>', '<tbody>', '</tbody>', '<tr>', '</tr>',
            '<td>', '</td>', '<th>', '</th>',
            '<div>', '</div>', '<p>', '</p>',
            '<ac:image', '</ac:image>', '<ac:structured-macro', '</ac:structured-macro>',
            '<ac:parameter', '</ac:parameter>', '<ac:rich-text-body>', '</ac:rich-text-body>'
        ]

        # Split content by newlines and process each line
        lines = content.split('\n')
        processed_lines = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip empty lines around block elements
            if not stripped:
                # Check if previous or next line is a block element
                prev_is_block = i > 0 and any(elem in lines[i-1] for elem in block_elements)
                next_is_block = i < len(lines) - 1 and any(elem in lines[i+1] for elem in block_elements)

                if prev_is_block or next_is_block:
                    continue  # Skip this empty line entirely
                else:
                    processed_lines.append('<br/>')  # Keep as line break for text content
            else:
                # Check if this line contains a block element
                is_block = any(elem in stripped for elem in block_elements)

                if is_block:
                    # Don't add <br/> for block elements
                    processed_lines.append(stripped)
                else:
                    # Regular text content - add it and a <br/> if not the last line
                    processed_lines.append(stripped)
                    if i < len(lines) - 1:
                        # Only add <br/> if the next line is not a block element
                        next_stripped = lines[i+1].strip() if i+1 < len(lines) else ''
                        next_is_block = any(elem in next_stripped for elem in block_elements)
                        if not next_is_block and not stripped.lower().endswith(('<br/>', '<br>', '<br />')):
                            processed_lines.append('<br/>')

        sanitized_content = ''.join(processed_lines)

        wrapper = f"<div>{sanitized_content}</div>"

        # First try strict validation.
        try:
            etree.fromstring(wrapper, etree.XMLParser(recover=False, resolve_entities=False, no_network=True))
            # Return the newline-sanitised content
            return sanitized_content
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
            raise ValueError(f"XHTML recovery failed: {exc}")
