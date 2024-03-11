from newspaper import Article


class NewspaperScraper:

    def __init__(self, link, session=None):
        self.link = link
        self.session = session

    def scrape(self) -> str:
        try:
            article = Article(
                self.link,
                language="en",
                memoize_articles=False,
                fetch_images=False,
            )
            article.download()
            article.parse()

            title = article.title
            text = article.text

            # If title, summary are not present then return None
            if not (title and text):
                return ""

            return f"{title} : {text}"

        except Exception as e:
            print("Error! : " + str(e))
            return ""
