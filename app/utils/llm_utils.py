import tiktoken
from langchain_community.embeddings import HuggingFaceEmbeddings, OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from app.config import Config
from app.utils.common import Common


def load_fast_llm():
    """
    The function `load_fast_llm()` returns an instance of the ChatOpenAI class with a temperature of 0.2
    and the FAST_LLM_MODEL configuration.
    :return: The function `load_fast_llm()` returns an instance of the `ChatOpenAI` class with a
    temperature of 0.2 and the model specified as `Config.FAST_LLM_MODEL`.
    """
    llm = ChatOpenAI(temperature=0.2, model=Config.FAST_LLM_MODEL)
    
    return llm


def get_embeddings():
    """
    The function `get_embeddings` returns embeddings using the Hugging Face model
    "sentence-transformers/all-MiniLM-L6-v2" on the CPU.
    :return: An instance of the HuggingFaceEmbeddings class initialized with the model
    "sentence-transformers/all-MiniLM-L6-v2" and device set to "cpu" is being returned.
    """
    
    print(f"Fetching embeddings!")
    
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )

    return embeddings


def get_text_splitter():
    """
    The function `get_text_splitter` returns an instance of the `RecursiveCharacterTextSplitter` class
    with specific parameters.

    Returns:
      an instance of the `RecursiveCharacterTextSplitter` class with the specified parameters
    `chunk_size=4000` and `chunk_overlap=100`.
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=100)

    return text_splitter


def split_text(docs):
    """
    The function `split_text` takes a list of documents as input and splits each document into smaller
    parts using a text splitter, returning the splits.

    Args:
      docs: The "docs" parameter is a list of documents that you want to split. Each document can be a
    string containing text.

    Returns:
      the splits of the input documents.
    """
    text_splitter = get_text_splitter()
    splits = text_splitter.split_documents(docs)

    return splits


def break_up_text(text, chunk_size=2000):
    """
    The `break_up_text` function takes a text and breaks it into chunks of a specified size, ensuring
    that each chunk ends with a complete sentence or a line break.

    Args:
      text: The `text` parameter is the input text that you want to break up into chunks. It can be a
    string containing any text you want to process.
      chunk_size: The `chunk_size` parameter determines the maximum size of each chunk of text that will
    be generated. If the input text is longer than the `chunk_size`, it will be broken up into multiple
    chunks. The default value for `chunk_size` is 2000, but you can change it to. Defaults to 2000
    """
    try:
        encoding = tiktoken.get_encoding("p50k_base")

        tokens = encoding.encode(text)
        while len(tokens) > chunk_size:
            # Decode all remaining tokens under limit
            chunk = encoding.decode(tokens[:chunk_size])
            # Determine best point `i` to truncate text and yield
            i = len(chunk) - 1
            while (chunk[i] != "\n") and (chunk[i - 1 : i + 1] != ". "):
                i -= 1
            yield chunk[:i].strip().strip("\n")
            # Tokenize remaining text and append to beginning of remaining tokens
            tokens = encoding.encode(chunk[i:]) + tokens[chunk_size:]
        # Decode remaining tokens and yield text
        yield encoding.decode(tokens).strip().strip("\n")

    except Exception as e:
        Common.exception_details("break_up_text", e)
        yield ""
