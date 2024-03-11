import os
import re

import mistune
import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.shared import Pt

from app.config import Config as GlobalConfig
from app.utils.common import Common
from app.utils.production import Production

from ....document import add_hyperlink
from ...utils.text import *


class TableExtractor:
    def __init__(self, dir_path: str):
        self.dir_path = dir_path
        self.tables = []
        self.tables_path = os.path.join(self.dir_path, "tables.txt")

    def read_tables(self):
        if GlobalConfig.GCP_PROD_ENV:
            return read_txt_files(self.dir_path, tables=True) or ""
        else:
            if os.path.isdir(self.dir_path):
                return read_txt_files(self.dir_path, tables=True)
            else:
                return ""

    def save_tables(self):
        # save tables
        if GlobalConfig.GCP_PROD_ENV:
            user_bucket = Production.get_users_bucket()
            blob = user_bucket.blob(self.tables_path)
            blob.upload_from_string(str(self.tables))
        else:
            os.makedirs(os.path.dirname(self.tables_path), exist_ok=True)
            write_to_file(self.tables_path, str(self.tables))

    def extract_tables(self, url: str) -> list:
        """
        Extract tables from a given URL excluding those with hyperlinks in values.

        Args:
        - url (str): The URL to scrape tables from.

        Returns:
        - list: List of dictionaries, each representing a table with title and values.
        """

        def extract_table_title(table) -> str:
            """
            Extract and process the title of a table.

            Args:
            - table: BeautifulSoup object representing a table.

            Returns:
            - str: Processed title of the table.
            """

            def process_table_title(title):
                # Removing Table numberings like "Table 1:", "Table1-", etc.
                cleaned_title = re.sub(
                    r"^\s*Table\s*\d+\s*[:\-]\s*", "", title, flags=re.IGNORECASE
                )
                return cleaned_title.strip()

            title = ""
            # Check for a caption tag within the table
            table_caption = table.find("caption")
            if table_caption:
                title = table_caption.get_text(strip=True)
            else:
                # If no caption, look at previous tags like h1, h2, etc.
                previous_tag = table.find_previous(
                    ["h1", "h2", "h3", "h4", "h5", "h6", "p"]
                )
                if previous_tag:
                    title = previous_tag.get_text(strip=True)

            return process_table_title(title)

        def extract_table_data(table) -> list:
            """
            Extract data from a table excluding rows with hyperlinks.

            Args:
            - table: BeautifulSoup object representing a table.

            Returns:
            - list: List of dictionaries, each representing a row in the table.
            """
            table_data = []
            rows = table.find_all("tr")

            header_dict = {}
            thead = table.find("thead")

            if thead:
                header_row = thead.find("tr")
                if header_row:
                    # Extract header names from thead
                    header_cells = header_row.find_all(["th", "td"])
                    header_names = [
                        cell.text.strip() for cell in header_cells if cell.text.strip()
                    ]
                    # Assuming the header row contains unique names for keys
                    header_dict = {
                        index: name for index, name in enumerate(header_names)
                    }

            if header_dict:
                table_data.append(header_dict)

            for row in rows[1:]:
                row_data = {}
                cells = row.find_all(["td", "th"])
                valid_row = False

                for idx, cell in enumerate(cells):
                    cell_text = cell.text.strip() if idx < len(header_dict) else ""

                    row_data[str(idx)] = cell_text

                    # Check if cell_text is valid (not in exclusion list)
                    if cell_text and cell_text not in [
                        "NA",
                        "n/a",
                        "na",
                        "-",
                        "",
                        "NaN",
                    ]:
                        valid_row = True

                if valid_row:
                    table_data.append(row_data)

            return {"title": extract_table_title(table), "values": table_data}

        def has_hyperlinks(table_data) -> bool:
            """
            Check if any values in the table data contain hyperlinks.

            Args:
            - table_data (list): List of dictionaries representing table data.

            Returns:
            - bool: True if hyperlinks are found, False otherwise.
            """
            for row in table_data:

                for value in row:
                    # Check if the value contains an <a> tag
                    if isinstance(value, str) and re.search(
                        r'<a\s+(?:[^>]*?\s+)?href=[\'"]([^\'"]*)[\'"]', value
                    ):
                        return True
            return False

        def filter_tables(table) -> bool:
            """
            The function `filter_tables` filters out tables based on specific criteria such as blank
            values, hyperlinks, titles, and column names.

            :param table: The `filter_tables` function takes a `table` parameter, which is expected to
            be a dictionary representing a table. The dictionary should have the following keys:
            :return: The function `filter_tables` returns a boolean value - `True` if the table passes
            all the exclusion criteria specified in the function, and `False` if the table fails any of
            the criteria.
            """
            try:
                # Exlcude tables where value field is blank
                if len(table["values"]) in [0, 1]:
                    return False

                # Exclude tables with hyperlinks
                if has_hyperlinks(table["values"]):
                    return False

                # Exclude tables with specific titles
                if table["title"].lower() in [
                    "",
                    "information related to the various screen readers",
                ]:
                    return False

                # Exclude tables with specific column names
                for column_name in table["values"][0].values():
                    if column_name.lower() in ["download"]:
                        return False

                return True

            except Exception as e:
                Common.exception_details("TableExtractor.filter_tables", e)
                return False

        try:
            if url.endswith(".pdf"):
                return [], url

            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            tables = soup.find_all("table")
            extracted_tables = []

            for table in tables:
                nested_tables = table.find_all("table")
                if not nested_tables:
                    table_struct = extract_table_data(table)

                    if filter_tables(table_struct):
                        extracted_tables.append(table_struct)

            return extracted_tables

        except requests.RequestException as e:
            print(f"🚩 Request Exception when scraping tables : {e}")
            return []
        except Exception as e:
            Common.exception_details("TableExtractor.extract_tables", e)
            return []

    def tables_to_html(self, list_of_tables: list, url: str) -> str:
        try:
            html_tables = []
            print(f"Received {len(list_of_tables)} tables...")

            for table in list_of_tables:
                title = table.get("title", "")
                values = table.get("values", [])
                if values == []:
                    continue

                # Create the table header row
                headers = list(values[0].values())
                header_row = (
                    "<tr><th style='font-size: 16px; border: 1px solid black; padding: 10px; text-align: center;'>"
                    + "</th><th style='border: 1px solid black; padding: 10px; text-align: center;'>".join(
                        headers
                    )
                    + "</th></tr>"
                )
                html_table = [header_row]

                # Create rows with data
                for row in values[1:]:
                    row_values = list(row.values())
                    row_str = "<tr>"
                    for val in row_values:
                        # Check if the value is missing or empty key
                        if val == "" or val is None:
                            val = "&nbsp;"  # Replace with a non-breaking space

                        # Check if the value is numerical
                        if self.is_numerical(str(val)):
                            align_style = "text-align: right;"
                        else:
                            align_style = "text-align: left;"

                        # Add border style to always have a border around the cell
                        row_str += f"<td style='font-size: 14px; border: 1px solid black; padding: 10px; {align_style}'>{str(val)}</td>"
                    row_str += "</tr>"
                    html_table.append(row_str)

                # Create the table HTML structure
                table_html = (
                    "<table style='border-collapse: collapse;'><tbody>"
                    + "\n".join(html_table)
                    + "</tbody></table>"
                )

                # Create the title with proper heading
                title_html = (
                    f"<p style='font-weight: bold; font-size: 18px;'>{title}</p>"
                )

                # Add the url of the table
                url_html = f"<br><a href='{url}' style='float: right; font-size: 12px;'>source</a>"

                # Combine title and table HTML
                final_table_html = title_html + table_html + url_html
                html_tables.append(final_table_html)

            return "<br><br><br>".join(html_tables)

        except Exception as e:
            Common.exception_details("TableExtractor.tables_to_html", e)
            return ""

    def add_tables_to_doc(self, document: Document):
        if not len(self.tables):
            return

        # Add "Data Tables" as a title before the tables section
        document.add_heading("Data Tables", level=1)

        # Adding tables to the Word document
        for tables_set in self.tables:
            tables_in_url = tables_set["tables"]
            url = tables_set["url"]
            for table_data in tables_in_url:
                self.add_table_to_doc(
                    document, table_data["title"], table_data["values"], url
                )

    def add_table_to_doc(
        self, document: Document, table_title: str, table_values: list, url: str
    ):
        try:

            def clean_text(text):
                """Remove spaces, new lines, and tabs from the text."""
                return text.replace("\n", " ").replace("\t", " ")

            document.add_heading(table_title, level=2)

            table = document.add_table(rows=1, cols=len(table_values[0]))

            table.style = "Table Grid"  # Applying table grid style to have borders

            # Set header rows as bold and add borders
            hdr_cells = table.rows[0].cells
            for i, key in enumerate(table_values[0].keys()):
                cell = hdr_cells[i]
                cell.text = clean_text(table_values[0][key])
                cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                cell.paragraphs[0].runs[0].font.bold = True
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(10)
                for border in cell._element.xpath(".//*"):
                    border_val = border.attrib.get("val")
                    if border_val is not None:
                        border.attrib.clear()
                        border.attrib["val"] = border_val
                    else:
                        border.attrib["val"] = "single"

            for row_data in table_values[1:]:
                row = table.add_row().cells
                for i, key in enumerate(row_data.keys()):
                    cell = row[i]
                    cell.text = clean_text(row_data[key])
                    if self.is_numerical(row_data[key]):
                        cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
                    else:
                        cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.size = Pt(10)
                    for border in cell._element.xpath(".//*"):
                        border_val = border.attrib.get("val")
                        if border_val is not None:
                            border.attrib.clear()
                            border.attrib["val"] = border_val
                        else:
                            border.attrib["val"] = "single"

            # Adding the table URL after the table with right alignment and as a hyperlink
            p = document.add_paragraph()
            p.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
            add_hyperlink(p, "source", url, True)

        except Exception as e:
            print(f"🚩 Exception in adding tables to word document : {e}")
            # Revert changes on any exception
            pass

    def get_combined_html(self, report: str):
        # Convert Markdown to HTML
        report_html = mistune.html(report)

        # Get the html of the tables
        tables_html = ""
        for tables_in_url in self.tables:
            current_tables = tables_in_url.get("tables", [])
            current_url = tables_in_url.get("url", "")
            tables_html += self.tables_to_html(current_tables, current_url)

        combined_html = report_html
        if len(tables_html):
            print(f"➕ Appending {len(self.tables)} tables to report...\n")
            combined_html += "<br><h2>Data Tables</h2><br>" + tables_html

        return combined_html

    @staticmethod
    def is_numerical(value: str) -> bool:
        """
        The function `is_numerical` checks if a given value is numerical, allowing for optional commas and a
        percentage sign at the end.

        Args:
        value (str): The value parameter is a string that represents a numerical value.

        Returns:
        The function is_numerical is returning a boolean value.
        """
        numerical_pattern = re.compile(r"^-?(\d{1,3}(,\d{3})*|\d+)?(\.\d+)?%?$")
        return bool(numerical_pattern.match(str(value).replace(",", "")))
