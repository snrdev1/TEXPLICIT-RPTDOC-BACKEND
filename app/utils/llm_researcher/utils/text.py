"""Text processing functions"""
import io
import os
import re
import urllib

import mistune
from docx import Document
from htmldocx import HtmlToDocx
from md2pdf.core import md2pdf
from weasyprint import HTML

from app.config import Config as GlobalConfig
from app.utils.production import Production

from ..scraper import *


def write_to_file(filename: str, text: str) -> None:
    """Write text to a file

    Args:
        text (str): The text to write
        filename (str): The filename to write to
    """
    with open(filename, "w", encoding="cp437", errors="ignore") as file:
        file.write(text)


async def save_markdown(path: str, text: str) -> str:
    if GlobalConfig.GCP_PROD_ENV:
        encoded_file_path = await _save_markdown_prod(path, text)

    else:
        encoded_file_path = await _save_markdown_dev(path, text)

    return encoded_file_path


async def _save_markdown_prod(path: str, text: str) -> str:
    user_bucket = Production.get_users_bucket()
    blob = user_bucket.blob(f"{path}.md")
    blob.upload_from_string(text, content_type="text/markdown")

    encoded_file_path = urllib.parse.quote(f"{path}.md")

    return encoded_file_path


async def _save_markdown_dev(path: str, text: str) -> str:
    # Write the report to markdown file
    write_to_file(f"{path}.md", text)

    encoded_file_path = urllib.parse.quote(f"{path}.md")

    return encoded_file_path


async def write_md_to_word(path: str, report: str):
    if GlobalConfig.GCP_PROD_ENV:
        encoded_file_path = await _write_md_to_word_prod(path, report)
    else:
        encoded_file_path = await _write_md_to_word_dev(path, report)

    return encoded_file_path


async def _write_md_to_word_prod(path: str, report: str) -> str:
    user_bucket = Production.get_users_bucket()

    # Convert Markdown to HTML
    html = mistune.html(report)
    doc = Document()
    HtmlToDocx().add_html_to_document(html, doc)

    # Create a temporary file-like object to save the updated document
    temp_doc_io = io.BytesIO()
    doc.save(temp_doc_io)
    temp_doc_io.seek(0)  # Reset the pointer to the beginning of the stream

    # Upload the Docx file to the bucket
    blob = user_bucket.blob(f"{path}.docx")
    blob.upload_from_file(
        temp_doc_io,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    encoded_file_path = urllib.parse.quote(f"{path}.docx")

    return encoded_file_path


async def _write_md_to_word_dev(path: str, report: str) -> str:
    # Convert Markdown to HTML
    html = mistune.html(report)
    doc = Document()
    HtmlToDocx().add_html_to_document(html, doc)

    doc.save(f"{path}.docx")

    encoded_file_path = urllib.parse.quote(f"{path}.docx")

    return encoded_file_path


async def write_md_to_pdf(path: str, report: str) -> str:
  
    if GlobalConfig.GCP_PROD_ENV:
        encoded_file_path = await _write_md_to_pdf_prod(path, report)

    else:
        encoded_file_path = await _write_md_to_pdf_dev(path, report)

    return encoded_file_path


async def _write_md_to_pdf_prod(path: str, report: str) -> str:
    user_bucket = Production.get_users_bucket()

    # Convert Markdown to HTML
    html = mistune.html(report)

    # Create a WeasyPrint HTML object
    html_obj = HTML(string=html)

    # Generate the PDF file
    pdf_bytes = html_obj.write_pdf()
    blob = user_bucket.blob(f"{path}.pdf")
    blob.upload_from_string(pdf_bytes, content_type="application/pdf")

    encoded_file_path = urllib.parse.quote(f"{path}.pdf")

    return encoded_file_path


async def _write_md_to_pdf_dev(path: str, report: str) -> str:
    # Convert Markdown to HTML
    html = mistune.html(report)

    # Create a WeasyPrint HTML object
    html_obj = HTML(string=html)

    # Generate the PDF file
    html_obj.write_pdf(f"{path}.pdf")

    encoded_file_path = urllib.parse.quote(f"{path}.pdf")

    return encoded_file_path


def read_txt_files(directory, tables=False):
    """
    The function reads research text files from a specified directory, either in a production or
    development environment.

    Args:
      directory: The directory parameter is the path to the directory where the text files are located.
      tables: The `tables` parameter is a boolean flag that indicates whether or not to extract tables
    from the text files. If `tables` is set to `True`, the function will extract tables from the text
    files. If `tables` is set to `False` (default), the function will only read. Defaults to False

    Returns:
      the variable "all_text".
    """
    print("📡 Reading research text files from : ", directory)

    if GlobalConfig.GCP_PROD_ENV:
        all_text = _read_text_files_prod(directory, tables)
    else:
        all_text = _read_text_files_dev(directory, tables)

    return all_text


def _read_text_files_prod(directory, tables=False):
    """
    The function `_read_text_files_prod` reads the content of text files in a specified directory and
    returns all the text concatenated together.

    Args:
      directory: The `directory` parameter is the name of the directory in the production bucket where
    the text files are located.
      tables: The `tables` parameter is a boolean flag that determines whether to include only the
    content of the "tables.txt" file or include the content of all ".txt" files in the specified
    directory. Defaults to False

    Returns:
      a string containing the content of all the text files in the specified directory.
    """
    bucket = Production.get_users_bucket()
    blobs = bucket.list_blobs(prefix=directory)
    all_text = ""
    for filename in blobs:
        print(f"📡 Filename : {filename}")
        if tables:
            if filename == "tables.txt":
                content = filename.download_as_text()
                print(f"📡 content : {content}")
                all_text += content + "\n"
        else:
            if filename.name.endswith(".txt"):
                content = filename.download_as_text()
                print(f"📡 content : {content}")
                all_text += content + "\n"

    return all_text


def _read_text_files_dev(directory, tables=False):
    """
    The function `_read_text_files_dev` reads the contents of text files in a given directory and
    returns the concatenated text.

    Args:
      directory: The directory parameter is the path to the directory where the text files are located.
      tables: The `tables` parameter is a boolean flag that determines whether to include the contents
    of a file named "tables.txt" in the `all_text` output. If `tables` is set to `True`, the function
    will only include the contents of "tables.txt" in the output. If `. Defaults to False

    Returns:
      a string containing the contents of all the text files in the specified directory. If the `tables`
    parameter is set to `True`, it only includes the contents of the "tables.txt" file.
    """
    all_text = ""
    for filename in os.listdir(directory):
        if tables:
            if filename == "tables.txt":
                with open(
                    os.path.join(directory, filename),
                    "r",
                    errors="ignore",
                ) as file:
                    all_text += file.read() + "\n"
        else:
            if filename.endswith(".txt"):
                with open(
                    os.path.join(directory, filename),
                    "r",
                    encoding="cp437",
                    errors="ignore",
                ) as file:
                    all_text += file.read() + "\n"

    return all_text


def md_to_pdf(input_file, output_file):
    md2pdf(
        output_file,
        md_content=None,
        md_file_path=input_file,
        css_file_path=None,
        base_url=None,
    )


def remove_roman_numerals(input_string):
    """
    The function `remove_roman_numerals` takes an input string and removes any occurrences of Roman
    numerals from it.

    Args:
      input_string: The input string is the string from which you want to remove Roman numerals.

    Returns:
      a string with all Roman numerals removed.
    """
    # Define a regular expression pattern for Roman numerals
    roman_numerals_pattern = r"\b[IVXLCDM]+\b"

    # Use re.sub() to replace Roman numerals with an empty string
    result_string = re.sub(roman_numerals_pattern, "", input_string)

    return result_string
