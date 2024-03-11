from langchain_community.document_loaders import WebBaseLoader


class WebBaseLoaderScraper:

    def __init__(self, link, session=None):
        self.link = link
        self.session = session

    def scrape(self) -> str:
        try:
            loader = WebBaseLoader(self.link)
            loader.requests_kwargs = {"verify": False}
            docs = loader.load()
            content = ""

            for doc in docs:
                content += doc.page_content

            return content

        except Exception as e:
            print("Error! : " + str(e))
            return ""
