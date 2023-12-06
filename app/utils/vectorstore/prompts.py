from langchain.prompts import PromptTemplate


def get_custom_document_prompt():
    """
    The function `get_custom_document_prompt()` returns a template for generating a prompt for a
    question and answer task using a given context and question.
    
    Returns:
      The function `get_custom_document_prompt()` returns a prompt template that can be used to generate
    a custom document prompt.
    """
    custom_prompt_template = """You are a helpful Artifial Intelligence Question and Answer bot who answer the question based on a "context".
        Example -
            Example Number 1 :
            - Context : The Theory of Relativity was developed by Albert Einstein
            - Question :  Who developed the Theory of Relativity?
            - AI Reponse :  The Theory of Relativity was developed by Albert Einstein.

            Example Number 2:
            - Context :  Marketing is the activity, set of institutions, and processes for creating, communicating, delivering, and exchanging offerings that have value for customers, clients, partners, and society at large.
            - Question :  How do you manage your finance?
            - AI Reponse :  I don't know

            Example Number 3 :
            - Context : Water boils at 100 degrees Celsius at sea level
            - Question :  What is the boiling point of water at sea level?
            - AI Reponse :  The boiling point of water at sea level is 100 degrees Celsius.

            Example Number 4:
            - Context : Artificial intelligence is the ability of machines to perform tasks that are typically associated with human intelligence.
            - Question : What is the safety measure taken in Steel?
            - AI Response : I don't know

            Example Number 5:
            - Context : 
            - Question : How to get over depression?
            - AI Response : I don't know

        Since the context does not contain the answer to the question in Example 2 and 4 and since the context was empty in Example 5, AI Reponse is "I don't know".
        In a similar way is context is not realted to answer or the context is empty Your final anwser should be "I don't know".
        While in example 1 and 2 the context contains an helpful answer, so the AI Responded with that answer.

        Remember the follwing points before providing any answer : 
        - If the answer is not present in the "context" then just say that "I don't know", don't try to make up an answer.
        - If the "context" is empty do not answer, say "I don't know" even if you know anwser.
        - Only return the helpful answer below and nothing else.

        The context and question are - 
        Context: {context}
        Question: {question}

        Helpful answer:
        """

    prompt = PromptTemplate(
        template=custom_prompt_template, input_variables=["context", "question"]
    )

    return prompt


def get_custom_knowledgeitem_prompt():
    """
    The function `get_custom_knowledgeitem_prompt` returns a template for generating a prompt to answer
    a question based on a given context and question.
    
    Returns:
      The function `get_custom_knowledgeitem_prompt()` returns a prompt template for generating a custom
    knowledge item prompt.
    """
    custom_prompt_template = """
        Answer the question based on the given context.
        If you do not know the answer, say "I am unable to provide an answer to this question". Do not try to make up an answer.
                
        The context and question are - 
        Context: {context}
        Question: {question}

        Only return the helpful answer below and nothing else.
        Helpful answer:
    """
    prompt = PromptTemplate(
        template=custom_prompt_template, input_variables=["context", "question"]
    )
    return prompt
