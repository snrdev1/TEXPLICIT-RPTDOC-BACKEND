"""Text processing functions"""
import json
import os
import re
import string
import urllib
from typing import Dict, Generator, Optional

import markdown
from docx import Document
from html2docx import html2docx
from md2pdf.core import md2pdf
from selenium.webdriver.remote.webdriver import WebDriver
from weasyprint import HTML

from app.config import Config as GlobalConfig
from app.utils.production import Production

from ..agent.llm_utils import create_chat_completion
from ..config import Config

CFG = Config()


def split_text(text: str, max_length: int = 8192) -> Generator[str, None, None]:
    """Split text into chunks of a maximum length

    Args:
        text (str): The text to split
        max_length (int, optional): The maximum length of each chunk. Defaults to 8192.

    Yields:
        str: The next chunk of text

    Raises:
        ValueError: If the text is longer than the maximum length
    """
    paragraphs = text.split("\n")
    current_length = 0
    current_chunk = []

    for paragraph in paragraphs:
        if current_length + len(paragraph) + 1 <= max_length:
            current_chunk.append(paragraph)
            current_length += len(paragraph) + 1
        else:
            yield "\n".join(current_chunk)
            current_chunk = [paragraph]
            current_length = len(paragraph) + 1

    if current_chunk:
        yield "\n".join(current_chunk)


def summarize_text(
    url: str, text: str, question: str, driver: Optional[WebDriver] = None
) -> str:
    """Summarize text using the OpenAI API

    Args:
        url (str): The url of the text
        text (str): The text to summarize
        question (str): The question to ask the model
        driver (WebDriver): The webdriver to use to scroll the page

    Returns:
        str: The summary of the text
    """
    if not text:
        return "Error: No text to summarize"

    summaries = []
    chunks = list(split_text(text))
    scroll_ratio = 1 / len(chunks)

    print(f"Summarizing url: {url} with total chunks: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        if driver:
            scroll_to_percentage(driver, scroll_ratio * i)

        # memory_to_add = f"Source: {url}\n" f"Raw content part#{i + 1}: {chunk}"

        # MEMORY.add_documents([Document(page_content=memory_to_add)])

        messages = [create_message(chunk, question)]

        summary = create_chat_completion(
            model=CFG.fast_llm_model,
            messages=messages,
            max_tokens=CFG.summary_token_limit,
        )
        summaries.append(summary)
        # memory_to_add = f"Source: {url}\n" f"Content summary part#{i + 1}: {summary}"

        # MEMORY.add_documents([Document(page_content=memory_to_add)])

    combined_summary = "\n".join(summaries)
    messages = [create_message(combined_summary, question)]

    final_summary = create_chat_completion(
        model=CFG.fast_llm_model, messages=messages, max_tokens=CFG.summary_token_limit
    )
    print("Final summary length: ", len(combined_summary))
    print(final_summary)

    return final_summary


def scroll_to_percentage(driver: WebDriver, ratio: float) -> None:
    """Scroll to a percentage of the page

    Args:
        driver (WebDriver): The webdriver to use
        ratio (float): The percentage to scroll to

    Raises:
        ValueError: If the ratio is not between 0 and 1
    """
    if ratio < 0 or ratio > 1:
        raise ValueError("Percentage should be between 0 and 1")
    driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {ratio});")


def create_message(chunk: str, question: str) -> Dict[str, str]:
    """Create a message for the chat completion

    Args:
        chunk (str): The chunk of text to summarize
        question (str): The question to answer

    Returns:
        Dict[str, str]: The message to send to the chat completion
    """
    return {
        "role": "user",
        "content": f'"""{chunk}""" Using the above text, answer in short the following'
        f' question: "{question}" -- if the question cannot be answered using the text,'
        " simply summarize the text. "
        "Include all factual information, numbers, stats etc if available.",
    }


def write_to_file(filename: str, text: str) -> None:
    """Write text to a file

    Args:
        text (str): The text to write
        filename (str): The filename to write to
    """
    with open(filename, "w", encoding="cp437", errors="ignore") as file:
        file.write(text)


async def save_markdown(task: str, path: str, text: str) -> str:
    """
    The function `save_markdown` saves a markdown file to a specified path, either in a production or
    development environment.

    Args:
      task (str): A string representing the task or purpose of the markdown file.
      path (str): The `path` parameter is a string that represents the file path where the markdown file
    will be saved.
      text (str): The `text` parameter is a string that represents the content of the markdown file that
    you want to save.

    Returns:
      the encoded file path.
    """
    if GlobalConfig.GCP_PROD_ENV:
        encoded_file_path = await _save_markdown_prod(task, path, text)

    else:
        encoded_file_path = await _save_markdown_dev(task, path, text)

    return encoded_file_path


async def _save_markdown_prod(task: str, path: str, text: str) -> str:
    """
    The function `_save_markdown_prod` saves a markdown file to a specified path in a user's production
    bucket and returns the encoded file path.

    Args:
      task (str): The `task` parameter is a string that represents the name or identifier of the task.
    It is used to create the file path for the markdown file.
      path (str): The `path` parameter is a string that represents the directory path where the markdown
    file will be saved.
      text (str): The `text` parameter is a string that represents the content of the markdown file that
    you want to save.

    Returns:
      the encoded file path of the uploaded markdown file.
    """
    file_path = f"{path}/{task}"
    user_bucket = Production.get_users_bucket()
    blob = user_bucket.blob(f"{file_path}.md")
    blob.upload_from_string(text, content_type="text/markdown")

    encoded_file_path = urllib.parse.quote(f"{file_path}.md")

    return encoded_file_path


async def _save_markdown_dev(task: str, path: str, text: str) -> str:
    """
    The function `_save_markdown_dev` saves a markdown text to a specified file path and returns the
    encoded file path.

    Args:
      task (str): The `task` parameter is a string that represents the name or identifier of the task or
    report. It is used to create the file name for the markdown file.
      path (str): The `path` parameter is a string that represents the directory path where the markdown
    file will be saved.
      text (str): The `text` parameter is a string that represents the content of the markdown file that
    you want to save.

    Returns:
      the encoded file path of the saved markdown file.
    """
    # Ensure that this file path exists
    os.makedirs(path, exist_ok=True)

    # Get the complete file path based reports folder, type of report
    file_path = os.path.join(path, task)

    # Write the report to markdown file
    write_to_file(f"{file_path}.md", text)

    encoded_file_path = urllib.parse.quote(f"{file_path}.md")

    return encoded_file_path


async def write_md_to_word(task: str, path: str, text: str):
    """
    The function `write_md_to_word` writes markdown text to a Word document and returns the encoded file
    path.

    Args:
      task (str): A string representing the task or purpose of the document.
      path (str): The `path` parameter is a string that represents the file path where the Word document
    will be saved.
      text (str): The `text` parameter is a string that represents the content of the Markdown file that
    you want to convert to a Word document.

    Returns:
      the encoded file path.
    """
    if GlobalConfig.GCP_PROD_ENV:
        encoded_file_path = await _write_md_to_word_prod(task, path, text)
    else:
        encoded_file_path = await _write_md_to_word_dev(task, path, text)

    return encoded_file_path


async def _write_md_to_word_prod(task: str, path: str, text: str) -> str:
    """
    The function `_write_md_to_word_prod` takes a task, path, and text as input, converts the text from
    Markdown to HTML, converts the HTML to a Word document, and uploads the Word document to a user's
    bucket in production. It then returns the encoded file path of the uploaded document.

    Args:
      task (str): The `task` parameter is a string that represents the name or identifier of the task.
    It is used to create the file name and path for the Word document.
      path (str): The `path` parameter is a string representing the directory path where the file will
    be saved.
      text (str): The `text` parameter in the `_write_md_to_word_prod` function is a string that
    contains the Markdown text that needs to be converted to a Word document.

    Returns:
      the encoded file path of the uploaded Word document.
    """
    file_path = f"{path}/{task}"
    user_bucket = Production.get_users_bucket()

    # Convert Markdown to HTML
    html = markdown.markdown(text)

    # html2docx() returns an io.BytesIO() object. The HTML must be valid.
    doc_bytes = html2docx(html, title=f"{task}.docx")
    print("doc_bytes : ", doc_bytes)
    blob = user_bucket.blob(f"{file_path}.docx")
    blob.upload_from_string(doc_bytes.getvalue())

    print(f"🎉 {task} written to {file_path}.docx")

    encoded_file_path = urllib.parse.quote(f"{file_path}.docx")

    return encoded_file_path


async def _write_md_to_word_dev(task: str, path: str, text: str) -> str:
    """
    The function `_write_md_to_word_dev` takes a task, path, and text as input, converts the text from
    Markdown to HTML, converts the HTML to a Word document, saves the Word document to the specified
    path, and returns the encoded file path.

    Args:
      task (str): The `task` parameter is a string that represents the name or identifier of the task.
    It is used to create the file name for the generated Word document.
      path (str): The `path` parameter is a string that represents the directory path where the file
    will be saved.
      text (str): The `text` parameter is a string that contains the Markdown text that you want to
    convert to a Word document.

    Returns:
      the encoded file path of the generated Word document.
    """
    # Ensure that this file path exists
    os.makedirs(path, exist_ok=True)

    # Get the complete file path based reports folder, type of report
    file_path = os.path.join(path, task)

    html = markdown.markdown(text)

    # html2docx() returns an io.BytesIO() object. The HTML must be valid.
    buf = html2docx(html, title=f"{task}.docx")

    with open(f"{file_path}.docx", "wb") as fp:
        fp.write(buf.getvalue())

    print(f"🎉 {task} written to {file_path}.docx")

    encoded_file_path = urllib.parse.quote(f"{file_path}.docx")

    return encoded_file_path


async def write_md_to_pdf(task: str, path: str, text: str) -> str:
    """
    The function `write_md_to_pdf` writes markdown text to a PDF file and returns the encoded file path.

    Args:
      task (str): A string representing the task or purpose of the PDF file.
      path (str): The `path` parameter is a string that represents the file path where the PDF file will
    be saved.
      text (str): The `text` parameter is a string that represents the content of the Markdown file that
    you want to convert to a PDF.

    Returns:
      the encoded file path as a string.
    """
    if GlobalConfig.GCP_PROD_ENV:
        encoded_file_path = await _write_md_to_pdf_prod(task, path, text)

    else:
        encoded_file_path = await _write_md_to_pdf_dev(task, path, text)

    return encoded_file_path


async def _write_md_to_pdf_prod(task: str, path: str, text: str) -> str:
    """
    The function `_write_md_to_pdf_prod` takes a task, path, and text as input, uploads the text as a
    Markdown file to a user's bucket, converts the Markdown to HTML, generates a PDF file from the HTML
    using WeasyPrint, uploads the PDF file to the user's bucket, and returns the encoded file path of
    the PDF file.

    Args:
      task (str): The `task` parameter is a string that represents the name or identifier of the task
    for which the Markdown file and PDF file will be created.
      path (str): The `path` parameter is a string representing the directory path where the files will
    be stored.
      text (str): The `text` parameter is a string that contains the content of the Markdown file that
    needs to be converted to PDF.

    Returns:
      the encoded file path of the PDF file that was generated.
    """
    file_path = f"{path}/{task}"
    user_bucket = Production.get_users_bucket()

    # Convert Markdown to HTML
    html = markdown.markdown(text)

    # Create a WeasyPrint HTML object
    html_obj = HTML(string=html)

    # Generate the PDF file
    pdf_bytes = html_obj.write_pdf()
    blob = user_bucket.blob(f"{file_path}.pdf")
    blob.upload_from_string(pdf_bytes, content_type="application/pdf")

    print(f"🎉 {task} written to {file_path}.pdf")

    encoded_file_path = urllib.parse.quote(f"{file_path}.pdf")

    return encoded_file_path


async def _write_md_to_pdf_dev(task: str, path: str, text: str) -> str:
    """
    The function `_write_md_to_pdf_dev` takes a task, path, and text as input, writes the text to a
    markdown file, converts the markdown to HTML, generates a PDF file using WeasyPrint, and returns the
    encoded file path of the PDF.

    Args:
      task (str): The `task` parameter is a string that represents the name or identifier of the task or
    report. It is used to create the file name for the markdown and PDF files.
      path (str): The `path` parameter is the directory path where the PDF file will be saved.
      text (str): The `text` parameter is a string that contains the content of the report in Markdown
    format.

    Returns:
      the encoded file path of the generated PDF file.
    """
    # Ensure that this file path exists
    os.makedirs(path, exist_ok=True)

    # Get the complete file path based reports folder, type of report
    file_path = os.path.join(path, task)

    # print("📡 path : ", path)
    # print("📡 file_path : ", file_path)

    # Convert Markdown to HTML
    html = markdown.markdown(text)

    # Create a WeasyPrint HTML object
    html_obj = HTML(string=html)

    # Generate the PDF file
    html_obj.write_pdf(f"{file_path}.pdf")

    print(f"🎉 {task} written to {file_path}.pdf")

    encoded_file_path = urllib.parse.quote(f"{file_path}.pdf")

    return encoded_file_path


def read_txt_files(directory):
    """
    The function `read_txt_files` reads research text files from a given directory, and returns the text
    from those files.

    Args:
      directory: The directory parameter is the path to the directory where the text files are located.

    Returns:
      The function `read_txt_files` returns the variable `all_text`.
    """
    print("📡 Reading research text files from : ", directory)

    if GlobalConfig.GCP_PROD_ENV:
        all_text = _read_text_files_prod(directory)
    else:
        all_text = _read_text_files_dev(directory)

    return all_text


def _read_text_files_prod(directory):
    """
    The function `_read_text_files_prod` reads all text files in a given directory from a production
    bucket and returns the concatenated content of all the files.

    Args:
      directory: The `directory` parameter is a string that represents the directory path where the text
    files are located.

    Returns:
      a string that contains the content of all the text files in the specified directory.
    """
    bucket = Production.get_users_bucket()
    blobs = bucket.list_blobs(prefix=directory)
    all_text = ""
    for filename in blobs:
        print(f"📡 Filename : {filename}")
        if filename.name.endswith(".txt"):
            content = filename.download_as_text()
            print(f"📡 content : {content}")
            all_text += content + "\n"

    return all_text


def _read_text_files_dev(directory):
    """
    The function `_read_text_files_dev` reads all text files in a given directory and returns the
    concatenated content of all the files.

    Args:
      directory: The "directory" parameter is a string that represents the path to the directory where
    the text files are located.

    Returns:
      a string that contains the contents of all the text files in the specified directory.
    """
    all_text = ""
    for filename in os.listdir(directory):
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
