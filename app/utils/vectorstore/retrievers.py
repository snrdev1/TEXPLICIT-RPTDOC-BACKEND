from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough


class Retriever:

    def __init__(self, user_id, query, llm, prompt, db):
        self.user_id = user_id
        self.query = query
        self.llm = llm
        self.prompt = prompt
        self.retriever = db.as_retriever()

    def vectorstore_retriever(self):
        rag_chain = (
            {"context": self.retriever, "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

        return rag_chain.invoke(self.query)
