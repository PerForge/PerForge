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
import ast
import json

from app.backend.integrations.reporting_base   import ReportingBase
from app.backend.integrations.report_registry  import ReportRegistry
from app.backend.integrations.grafana.grafana  import Grafana
from app.backend.components.graphs.graphs_db   import DBGraphs
from io                                       import BytesIO
from PIL                                      import Image as PILImage
from reportlab.lib.colors                     import Color
from reportlab.lib.enums                      import TA_LEFT
from reportlab.lib.pagesizes                  import A4, landscape
from reportlab.lib.styles                     import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units                      import inch
from reportlab.lib.utils                      import ImageReader
from reportlab.pdfbase                        import ttfonts
from reportlab.pdfbase.pdfmetrics             import registerFont, registerFontFamily
from reportlab.platypus                       import (BaseDocTemplate, Frame, Image, PageTemplate, Paragraph, Spacer, Table, TableStyle)
from datetime                                 import datetime


class Pdf:

    def __init__(self, pdf_io, margin=15):
        self.doc              = BaseDocTemplate(pdf_io, pagesize=landscape(A4), leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=margin)
        self.elements         = []
        self.text_color       = Color(206 / 255, 213 / 255, 218 / 255)
        self.header_color     = Color(40 / 255, 40 / 255, 40 / 255)
        self.background_color = Color(60 / 255, 60 / 255, 60 / 255)
        self.logo_path        = os.path.join('app', 'static', 'assets', 'img', 'logo.png')
        registerFont(ttfonts.TTFont('NunitoSans', os.path.join('app', 'static', 'assets', 'fonts', 'NunitoSans_7pt-Regular.ttf')))
        registerFont(ttfonts.TTFont('NunitoSans-Bold', os.path.join('app', 'static', 'assets', 'fonts', 'NunitoSans_7pt-Bold.ttf')))
        registerFontFamily('NunitoSans', normal='NunitoSans', bold='NunitoSans-Bold')
        self.title_font    = 'NunitoSans-Bold'
        self.regular_font  = 'NunitoSans'
        self.header_height = 50
        self.title_size    = 14

        # Create a custom page template with a gray background
        def on_page(canvas, doc):
            canvas.setFillColor(self.background_color)
            canvas.rect(0, 0, landscape(A4)[0], landscape(A4)[1], fill=1, stroke=0)
            # Check if it's the first page
            if doc.page == 1:
                draw_header(canvas)

        def draw_header(canvas):
            # Adjust the y-coordinate of the rectangle to move it closer to the top
            header_radius    = 10
            header_text_size = 16
            rect_y           = landscape(A4)[1] - self.header_height

            # Draw the new rectangle with full width and rounded bottom edges
            canvas.setFillColor(self.header_color)
            canvas.roundRect(0, rect_y, landscape(A4)[0], 60, header_radius, fill=1, stroke=0)

            # Add the logo
            logo = ImageReader(self.logo_path)
            logo_width, logo_height = logo.getSize()
            logo_scale        = 40 / logo_height  # Scale the logo to fit the rectangle height
            logo_width_scaled = logo_width * logo_scale

            # Add the title
            title_text = "PerForge"
            canvas.setFont(self.title_font, header_text_size)
            canvas.setFillColor(self.text_color)
            title_width = canvas.stringWidth(title_text, self.title_font, header_text_size)

            # Calculate the combined width and adjust positions
            combined_width = logo_width_scaled + title_width
            logo_x         = (landscape(A4)[0] - combined_width) / 2
            title_x        = logo_x + logo_width_scaled

             # Draw the logo and title
            logo_y = rect_y + (self.header_height - logo_height * logo_scale) / 2  # Vertically center the logo within the rectangle
            canvas.drawImage(self.logo_path, logo_x, logo_y, logo_width_scaled, logo_height * logo_scale, mask='auto')

            # Calculate the title height and adjust the position
            title_height = header_text_size * 0.8
            title_y      = rect_y + (self.header_height - title_height) / 2
            canvas.drawString(title_x, title_y, title_text)

        frame = Frame(margin, margin, self.doc.width, self.doc.height, id='normal', showBoundary=0)
        self.doc.addPageTemplates([PageTemplate(id='GrayBackground', frames=frame, onPage=on_page)])

    def add_title(self, title_text):
        styles      = getSampleStyleSheet()
        title_style = ParagraphStyle(
            name      = 'Title',
            parent    = styles['Heading1'],
            fontSize  = self.title_size,
            alignment = TA_LEFT,
            textColor = self.text_color,
            fontName  = self.title_font
        )
        title = Paragraph(title_text, title_style)
        self.elements.append(Spacer(1, 0.25 * inch))
        self.elements.append(title)

    def add_image(self, image):
        image_io = BytesIO(image)
        img      = PILImage.open(image_io)
        img_width, img_height = img.size
        max_width  = landscape(A4)[0] - self.doc.leftMargin - self.doc.rightMargin
        max_height = landscape(A4)[1] - self.doc.topMargin - self.doc.bottomMargin - 0.25 * inch  # Subtract the height of the Spacer
        if img_width > max_width:
            img_height = img_height * (max_width / img_width)
            img_width  = max_width
        if img_height > max_height:
            img_width  = img_width * (max_height / img_height)
            img_height = max_height
        # Create a new BytesIO object for the resized image
        resized_image_io = BytesIO()
        img.save(resized_image_io, format=img.format)
        resized_image_io.seek(0)
        img = RoundedImage(resized_image_io, width=img_width, height=img_height)
        self.elements.append(Spacer(1, 0.25 * inch))
        self.elements.append(img)

    def add_table(self, table_data):
        # Process data to handle long text and create paragraphs for cell content
        processed_data = []
        max_chars_per_cell = 40  # Maximum characters before forcing a line break
        styles = getSampleStyleSheet()
        cell_style = styles['Normal']
        cell_style.fontName = self.regular_font
        cell_style.textColor = self.text_color
        cell_style.fontSize = 8

        header_style = styles['Normal']
        header_style.fontName = self.title_font
        header_style.textColor = self.text_color
        header_style.fontSize = 9

        # Process headers (first row)
        header_row = []
        for cell in table_data[0]:
            # Replace various forms of null values with 0
            if cell is None or cell == '' or cell == 'None' or (isinstance(cell, float) and (cell != cell)):  # None, empty string, 'None' string, and NaN
                cell = 0
            cell_text = str(cell)
            header_row.append(Paragraph(cell_text, header_style))
        processed_data.append(header_row)

        # Process data rows
        for row in table_data[1:]:
            processed_row = []
            for cell in row:
                # Replace various forms of null values with 0
                if cell is None or cell == '' or cell == 'None' or (isinstance(cell, float) and (cell != cell)):  # None, empty string, 'None' string, and NaN
                    cell = 0
                cell_text = str(cell)
                # Add soft breaks for long text
                if len(cell_text) > max_chars_per_cell:
                    # Insert soft breaks to help with wrapping
                    parts = [cell_text[i:i+max_chars_per_cell] for i in range(0, len(cell_text), max_chars_per_cell)]
                    cell_text = '<br/>'.join(parts)
                processed_row.append(Paragraph(cell_text, cell_style))
            processed_data.append(processed_row)

        # Calculate table width and column widths
        available_width = landscape(A4)[0] - self.doc.leftMargin - self.doc.rightMargin - 10  # Extra margin for safety
        num_columns = len(table_data[0])

        # Use equal column widths across the full page width
        col_width = available_width / num_columns
        col_widths = [col_width] * num_columns

        # Create table with the calculated column widths
        table = Table(processed_data, colWidths=col_widths, cornerRadii=[6, 6, 6, 6])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.header_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.text_color),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), self.title_font),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), self.background_color),
            ('TEXTCOLOR', (0, 1), (-1, -1), self.text_color),
            ('GRID', (0, 0), (-1, -1), 1, self.header_color),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            # These settings force proper wrapping
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))

        self.elements.append(Spacer(1, 0.25 * inch))
        self.elements.append(table)

    def add_text(self, text):
        styles                 = getSampleStyleSheet()
        normal_style           = styles["Normal"]
        normal_style.fontName  = self.regular_font
        normal_style.textColor = self.text_color
        text                   = text.replace('\n', '<br/>')
        self.elements.append(Spacer(1, 0.25 * inch))
        self.elements.append(Paragraph(text, normal_style))

    def add_text_summary(self, text):
        styles                 = getSampleStyleSheet()
        normal_style           = styles["Normal"]
        normal_style.fontName  = self.regular_font
        normal_style.textColor = self.text_color
        text                   = text.replace('\n', '<br/>')
        self.elements.insert(3, Paragraph(text, normal_style))

    def build(self):
        self.doc.build(self.elements)

class RoundedImage(Image):

    def __init__(self, filename_or_object, width=None, height=None, kind='direct', mask=None, hAlign='CENTER', useDPI=False, rounded_corner_radius=6):
        super().__init__(filename_or_object, width, height, kind, mask, hAlign)
        self.rounded_corner_radius = rounded_corner_radius

    def draw(self):
            self.canv.saveState()
            path = self.canv.beginPath()
            path.roundRect(0, 0, self.drawWidth, self.drawHeight, self.rounded_corner_radius)
            self.canv.clipPath(path, stroke=0)
            super().draw()
            self.canv.restoreState()

@ReportRegistry.register("pdf_report")
class PdfReport(ReportingBase):

    def __init__(self, project):
        super().__init__(project)
        self.pdf_io      = BytesIO()
        self.pdf_creator = Pdf(self.pdf_io)
        self.pdf_creator.elements.append(Spacer(1, self.pdf_creator.header_height))

    def set_template(self, template, influxdb):
        super().set_template(template, influxdb)

    def add_graph(self, graph_data, current_run_id, baseline_run_id):
        # Use the timestamps from current_test_obj instead of direct attributes
        start_timestamp = self.current_test_obj.start_time_timestamp
        end_timestamp = self.current_test_obj.end_time_timestamp
        test_name = self.current_test_obj.application

        image = self.grafana_obj.render_image(graph_data, start_timestamp, end_timestamp, test_name, current_run_id, baseline_run_id)
        self.pdf_creator.add_image(image)
        if self.ai_switch and self.ai_graph_switch and graph_data["prompt_id"]:
            ai_support_response = self.ai_support_obj.analyze_graph(graph_data["name"], image, graph_data["prompt_id"])
            if self.ai_to_graphs_switch:
                self.add_text(ai_support_response)

    def add_group_text(self, text):
        self.pdf_creator.add_text(text)

    def add_text(self, text):
        text  = self.replace_variables(text)
        table = self.check_if_table(text)
        if table == None:
            self.pdf_creator.add_text(text)
        else:
            self.pdf_creator.add_table(table)

    def check_if_table(self, text):
        try:
            # Attempt to parse the input string as a Python literal
            text   = text.replace('\\"', '"')
            result = ast.literal_eval(text)

            # Check if the result is a list of lists
            if isinstance(result, list) and all(isinstance(item, list) for item in result):
                return result
            else:
                return None  # Not a valid list of lists
        except (SyntaxError, ValueError):
            return None  # Parsing failed

    def generate_title(self, isgroup):
        if isgroup:
            title = self.group_title
        else:
            title = self.replace_variables(self.title)
        return title

    def format_table(self, metrics):
        """
        Format a metrics table for PDF report. Converts the list of dictionaries
        into a list of lists suitable for PDF table creation.

        Args:
            metrics: A list of dictionaries containing the metrics data

        Returns:
            A JSON string representation of a list of lists with table data
        """

        if not metrics:
            return json.dumps([["No data available"]])

        # Create header from the keys in the first dictionary
        all_keys = set()
        for record in metrics:
            all_keys.update(record.keys())

        # Filter out metadata fields (_baseline, _diff, _diff_pct, _color)
        keys = [k for k in sorted(all_keys) if not (k.endswith('_baseline') or 
                                k.endswith('_diff') or 
                                k.endswith('_diff_pct') or 
                                k.endswith('_color'))]
        
        # Make sure transaction is the first column
        if 'transaction' in keys:
            keys.remove('transaction')
            keys.insert(0, 'transaction')
        # Fallback to page if no transaction column
        elif 'page' in keys:
            keys.remove('page')
            keys.insert(0, 'page')
            
        # Create the table data structure with header row
        table_data = [keys]

        # Add rows for each record
        for record in metrics:
            # Get each value and replace None or empty values with ''
            row = []
            for key in keys:
                value = record.get(key, '')
                if value is None or value == 'None' or (isinstance(value, float) and (value != value)):
                    value = 0
                row.append(value)
            table_data.append(row)

        # Convert any numerical values to more readable format
        for i in range(1, len(table_data)):
            for j in range(len(table_data[i])):
                if isinstance(table_data[i][j], float):
                    table_data[i][j] = f"{table_data[i][j]:.2f}"

        # Return the table data as a JSON string
        return json.dumps(table_data)

    def generate_report(self, tests, influxdb, template_group=None):
        templates_title = ""
        group_title     = None
        def process_test(test):
            nonlocal templates_title
            template_id = test.get('template_id')
            if template_id:
                self.set_template(template_id, influxdb)
                run_id          = test.get('test_title')
                baseline_run_id = test.get('baseline_test_title')
                self.collect_data(run_id, baseline_run_id)
                title = self.generate_title(False)
                self.pdf_creator.add_title(title)
                self.generate(run_id, baseline_run_id)
                if not group_title:
                    templates_title += f'{title}_'
        if template_group:
            self.set_template_group(template_group)
            group_title           = self.generate_title(True)
            self.pdf_creator.add_title(group_title)
            for obj in self.template_order:
                if obj["type"] == "text":
                    self.add_group_text(obj["content"])
                elif obj["type"] == "template":
                    for test in tests:
                        if obj.get('id') == test.get('template_id'):
                            process_test(test)
        else:
            for test in tests:
                process_test(test)
        current_time = datetime.now()
        time_str     = current_time.strftime("%d%m%Y-%H%M")
        if not group_title:
            templates_title += time_str
        else:
            templates_title = group_title + time_str
        self.pdf_creator.build()
        response = self.generate_response()
        response['filename'] = templates_title
        return response

    def generate(self, current_run_id, baseline_run_id = None):
        if self.nfrs_switch or self.ai_switch or self.ml_switch:
            self.analyze_template()
        for obj in self.data:
            if obj["type"] == "text":
                self.add_text(obj["content"])
            elif obj["type"] == "graph":
                graph_data       = DBGraphs.get_config_by_id(project_id=self.project, id=obj["graph_id"])
                self.grafana_obj = Grafana(project=self.project, id=graph_data["grafana_id"])
                self.add_graph(graph_data, current_run_id, baseline_run_id)
