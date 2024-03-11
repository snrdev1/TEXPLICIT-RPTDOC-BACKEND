from langchain_community.document_loaders import PyMuPDFLoader


class PyMuPDFScraper:

    def __init__(self, link, session=None):
        self.link = link
        self.session = session

    def scrape(self) -> str:
        loader = PyMuPDFLoader(self.link)
        doc = loader.load()
        return str(doc)
