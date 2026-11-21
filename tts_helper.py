import os
import queue
import threading
import time
from gtts import gTTS
from playsound import playsound

_tts_queue = queue.Queue()
_running = True

def _tts_worker():
    """Background thread to process the speech queue sequentially"""
    while _running:
        try:
            text = _tts_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        if text:
            try:
                # Save TTS to temporary file
                filename = f"tts_{int(time.time()*1000)}.mp3"
                tts = gTTS(text=text, lang="en", slow=False, tld="com")
                tts.save(filename)

                # Play audio
                playsound(filename)

                # Cleanup
                if os.path.exists(filename):
                    os.remove(filename)

            except Exception as e:
                print(f"❌ TTS error: {e}")
        _tts_queue.task_done()


# Start worker thread
_thread = threading.Thread(target=_tts_worker, daemon=True)
_thread.start()


def speak_with_gemini(text: str):
    """
    Add text to the TTS queue (non-blocking).
    """
    if not text or not text.strip():
        return
    print(f"🔊 Speaking: {text[:60]}{'...' if len(text) > 60 else ''}")
    _tts_queue.put(text)


def stop_tts():
    """
    Stop all speech immediately and clear the queue.
    """
    global _running
    while not _tts_queue.empty():
        try:
            _tts_queue.get_nowait()
            _tts_queue.task_done()
        except queue.Empty:
            break
    # playsound can’t be interrupted mid-play easily,
    # but we prevent future queued items


def shutdown_tts():
    """
    Cleanly shutdown TTS thread on program exit.
    """
    global _running
    _running = False
    stop_tts()
    time.sleep(0.2)
