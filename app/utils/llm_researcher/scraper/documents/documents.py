from app.services.my_documents_service import MyDocumentsService
from app.utils.vectorstore.base import VectorStore
from app.utils.llm_utils import get_embeddings

def retrieve_context_from_documents(user_id, query: str, max_docs: int = 15, score_threshold: float = 1.2):
    """
    The function `retrieve_context_from_documents` retrieves relevant documents based on a user query,
    filters them based on a score threshold, and constructs a context by formatting the extracted
    document excerpts.
    
    Args:
      user_id: The user_id is a unique identifier for the user. It is used to retrieve the document
    vectorstore and original files associated with the user.
      query (str): The query is the text that you want to search for in the documents. It can be a
    single word, a phrase, or a sentence.
      max_docs (int): The `max_docs` parameter specifies the maximum number of documents to retrieve as
    part of the context. By default, it is set to 15. Defaults to 15
      score_threshold (float): The `score_threshold` parameter is a threshold value used to filter the
    relevant documents based on their scores. Any document with a score higher than the
    `score_threshold` will be excluded from the final list of relevant documents.
    
    Returns:
      The function `retrieve_context_from_documents` returns the context, which is a string containing
    the formatted excerpts from relevant documents.
    """    
    # Retrieve embeddings
    embeddings = get_embeddings()

    # Embed query
    embedded_query = embeddings.embed_query(query)

    # Get the document vectorstore
    db = VectorStore(user_id).get_document_vectorstore()
    
    context = ""
    if db:

      # Get the relevant docs from the vectorstore
      relevant_docs = db.max_marginal_relevance_search_with_score_by_vector(
          embedded_query, k=max_docs, fetch_k=max_docs + 50
      )

      # Filter all relevant docs using score
      scored_docs = [doc for doc in relevant_docs if doc[1] <= score_threshold]

      # Extract all virtual filenames
      virtual_filenames = [doc[0].metadata["source"] for doc in scored_docs]

      # Get all original files from the DB using virtual filenames
      original_files = MyDocumentsService().get_all_files_by_virtual_name(
          user_id, virtual_filenames
      )

      # Get the original filenames from the data loaded from DB
      filenames = [file["originalFileName"] for file in original_files]

      # Format the extracted docs in suitable format to construct the context
      processed_docs = [
          f"Excerpt from file {filename} : {doc[0].page_content}"
          for filename, doc in zip(filenames, scored_docs)
      ]

      # Appending the formatted docs to form the context
      context = ("\n").join(processed_docs)

      print(f"💎 Found {len(processed_docs)} relevant docs...")

    return context, filenames
