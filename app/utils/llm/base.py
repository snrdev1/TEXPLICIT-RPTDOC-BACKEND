from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from app.utils.common import Common
import tiktoken

encoding = tiktoken.get_encoding("p50k_base")

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
        tokens = encoding.encode(text)
        while len(tokens) > chunk_size:
            # Decode all remaining tokens under limit
            chunk = encoding.decode(tokens[:chunk_size])
            # Determine best point `i` to truncate text and yield 
            i = len(chunk) - 1
            while (chunk[i] != "\n") and (chunk[i-1:i+1] != ". "):
                i -= 1
            yield chunk[:i].strip().strip("\n")
            # Tokenize remaining text and append to beginning of remaining tokens
            tokens = encoding.encode(chunk[i:]) + tokens[chunk_size:]
        # Decode remaining tokens and yield text    
        yield encoding.decode(tokens).strip().strip("\n")
    
    except Exception as e:
        Common.exception_details("break_up_text", e)
        yield ""
