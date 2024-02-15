from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough


class Retriever:

    def __init__(self, user_id, query, llm, prompt, db):
        self.user_id = user_id
        self.query = query
        self.llm = llm
        self.prompt = prompt
        self.retriever = db.as_retriever()

    def rag_chain_without_sources(self):
        rag_chain = (
            {"context": self.retriever, "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

        return rag_chain.invoke(self.query)

    def rag_chain_with_sources(self):
        rag_chain_from_docs = (
            RunnablePassthrough.assign(
                context=(lambda x: self._format_docs(x["context"]))
            )
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

        rag_chain_with_source = RunnableParallel(
            {"context": self.retriever, "question": RunnablePassthrough()}
        ).assign(answer=rag_chain_from_docs)

        response_dict = rag_chain_with_source.invoke(self.query)

        response = response_dict.get("answer", "")

        sources = (
            list(
                set(
                    [
                        document.metadata["source"]
                        for document in response_dict["context"]
                    ]
                )
            )
            or []
        )

        return response, sources

    def _format_docs(self, docs):
        return "\n\n".join(doc.page_content for doc in docs)
