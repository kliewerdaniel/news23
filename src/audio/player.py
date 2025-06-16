import queue
import threading
import io
import logging
from pydub import AudioSegment
from pydub.playback import play

def play_audio_from_queue(audio_queue: queue.Queue):
    """
    Continuously fetches audio data from a queue and plays it.
    Runs in a separate thread.
    """
    while True:
        try:
            audio_data = audio_queue.get()
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
            play(audio_segment)
            audio_queue.task_done()
        except Exception as e:
            logging.error(f"Audio playback error: {e}")
            continue
