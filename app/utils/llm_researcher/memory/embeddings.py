from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings


class Memory:
    def __init__(self, **kwargs):
        self._embeddings = OpenAIEmbeddings(disallowed_special=())

    def get_embeddings(self):
        return self._embeddings

