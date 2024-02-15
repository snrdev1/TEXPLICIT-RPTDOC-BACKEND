import os

import soundfile as sf
from google.cloud import storage
from nltk.tokenize import sent_tokenize
from openai import OpenAI

from app.config import Config
from app.utils.common import Common
from app.utils.production import Production


class AudioGenerator:

    def __init__(self, dir: str, text: str, chunk_size: int = 4096):
        self.dir = dir
        self.text = text
        self.chunk_size = chunk_size

    def tts(self):
        if Config.GCP_PROD_ENV:
            return self._tts_prod()
        else:
            return self._tts_dev()

    def _chunk_text(self):
        # Split the text into sentences using NLTK
        sentences = sent_tokenize(self.text)

        # Initialize variables
        current_chunk = ""
        chunks = []

        for sentence in sentences:
            # Check if adding the current sentence exceeds the chunk_size
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence + " "
            else:
                # If adding the sentence exceeds the chunk_size, start a new chunk
                chunks.append(current_chunk.strip())
                current_chunk = sentence + " "

        # Add the last chunk
        chunks.append(current_chunk.strip())

        return chunks

    def _tts_dev(self):
        try:
            client = OpenAI(api_key=Config.OPENAI_API_KEY)

            # Chunk the text into complete sentences
            text_chunks = self._chunk_text()

            # Ensure that the output folder exists
            os.makedirs(self.dir, exist_ok=True)

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
                file_path = os.path.join(self.dir, "audio_chunks", audio_chunk_path)

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
            output_file_path = os.path.join(self.dir, "report_audio.wav")
            sf.write(output_file_path, combined_audio, 22050, subtype="PCM_16")

            print(f"🎵 Combined audio saved to {dir}")

            return output_file_path

        except Exception as e:
            Common.exception_details("_tts_dev", e)
            return ""

    def _tts_prod(self):
        try:
            pass

        except Exception as e:
            Common.exception_details("_tts_prod", e)
            return ""
