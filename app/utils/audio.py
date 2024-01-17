from app.config import Config
from app.utils.common import Common
import os
from openai import OpenAI
import soundfile as sf
import os
from nltk.tokenize import sent_tokenize

def chunk_text(text, chunk_size):
    # Split the text into sentences using NLTK
    sentences = sent_tokenize(text)

    # Initialize variables
    current_chunk = ""
    chunks = []

    for sentence in sentences:
        # Check if adding the current sentence exceeds the chunk_size
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += sentence + " "
        else:
            # If adding the sentence exceeds the chunk_size, start a new chunk
            chunks.append(current_chunk.strip())
            current_chunk = sentence + " "

    # Add the last chunk
    chunks.append(current_chunk.strip())

    return chunks

def tts(dir: str, text: str):
    try:
        client = OpenAI(api_key=Config.OPENAI_API_KEY)

        # Set your desired chunk size
        chunk_size = 4096

        # Chunk the text into complete sentences
        text_chunks = chunk_text(text, chunk_size)

        # Ensure that the output folder exists
        os.makedirs(dir, exist_ok=True)

        # List to store audio segments
        audio_segments = []

        # Generate audio responses for each chunk
        for i, chunk in enumerate(text_chunks):
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=chunk,
            )

            audio_chunk_path = f"report_audio_{i}.wav"
            file_path = os.path.join(dir, "audio_chunks", audio_chunk_path)

            # Ensure that the directory structure exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            response.stream_to_file(file_path)

            # Append the audio segment to the list
            audio_segments.append(file_path)

        # Concatenate audio files
        combined_audio = []

        for file_path in audio_segments:
            audio_chunk, _ = sf.read(file_path, dtype="int16")
            combined_audio.extend(audio_chunk)

        # Write the combined audio to a new file
        output_filename = os.path.join(dir, "report_audio.wav")
        sf.write(output_filename, combined_audio, 22050, subtype="PCM_16")

        print(f"🎵 Combined audio saved to {dir}")

        return output_filename

    except Exception as e:
        Common.exception_details("tts", e)
        return ""
