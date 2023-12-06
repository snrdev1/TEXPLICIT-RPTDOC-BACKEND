import json

from newspaper import Article

from app.utils.llm.llm_summarizer import summarize_text


class WebScraper:

    @staticmethod
    def scrape(url):
        """
        The function `scrape` takes a URL as input, scrapes the article content from the webpage, and
        returns information such as the article title, authors, publication date, top image, text,
        keywords, and a summary of the article.
        
        Args:
          url: The URL of the webpage you want to scrape.
        
        Returns:
          a dictionary containing information about the scraped article. The dictionary includes the
        following keys: "title", "keywords", "summary", "url", "authors", "pub_date", and "image".
        """

        try:

            article = Article(url, language="en",
                              memoize_articles=False, fetch_images=True, request_timeout=15)
            article.download()
            article.parse()

            title = article.title
            authors = article.authors
            pub_date = article.publish_date
            image = article.top_image
            text = article.text

            article.nlp()
            keywords = article.keywords

            # Newspaper library summary
            # summary = article.summary

            # LLM summary
            # summary = summarize_text(text)

            summary = text

            # If title, summary are not present then return None
            if not (title and summary) or len(summary) < 300:
                return None

            article_info = {
                "title": title,
                "keywords": keywords,
                "summary": summary,
                "url": url,
                "authors": authors,
                "pub_date": json.dumps(pub_date, default=str),
                "image": image
            }

            return article_info

        except Exception as e:
            print("Error! : " + str(e))
            return
