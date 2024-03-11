from .scraper import Scraper
from .documents.documents import retrieve_context_from_documents
from .tables.tables import TableExtractor
from .beautiful_soup.beautiful_soup import BeautifulSoupScraper
from .newspaper.newspaper import NewspaperScraper
from .web_base_loader.web_base_loader import WebBaseLoaderScraper
from .arxiv.arxiv import ArxivScraper
from .pymupdf.pymupdf import PyMuPDFScraper

__all__ = [
    "Scraper",
    "retrieve_context_from_documents",
    "TableExtractor",
    "BeautifulSoupScraper",
    "NewspaperScraper",
    "WebBaseLoaderScraper",
    "ArxivScraper",
    "PyMuPDFScraper"
]
