"""# voice_controller.py
import threading
import speech_recognition as sr
from PySide6.QtCore import QObject, Signal

class VoiceController(QObject):
    text_recognized = Signal(str)  # ✅ Signal for recognized text

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self._running = False

    def start_listening(self):
        if self._running:
            return
        self._running = True
        thread = threading.Thread(target=self._listen_loop, daemon=True)
        thread.start()

    def stop_listening(self):
        self._running = False

    def _listen_loop(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            while self._running:
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=8)
                    text = self.recognizer.recognize_google(audio)
                    print(f"🗣️ You said: {text}")
                    # ✅ Emit signal instead of calling Gemini directly
                    self.text_recognized.emit(text)
                except sr.UnknownValueError:
                    print("❌ Could not understand audio")
                except sr.RequestError as e:
                    print(f"⚠️ API error: {e}")
                except Exception as e:
                    print(f"⚠️ Unexpected error: {e}")

# voice_controller.py
import threading
import speech_recognition as sr
from PySide6.QtCore import QObject, Signal

class VoiceController(QObject):
    # Emits only when a valid Gemini command is detected
    text_recognized = Signal(str)

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self._running = False

    def start_listening(self):
        if self._running:
            return
        self._running = True
        thread = threading.Thread(target=self._listen_loop, daemon=True)
        thread.start()

    def stop_listening(self):
        self._running = False

    def _listen_loop(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            print("🎤 Voice controller is listening for keyword 'Gemini'...")
            while self._running:
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=8)
                    text = self.recognizer.recognize_google(audio)
                    print(f"🗣️ You said: {text}")

                    # ✅ Keyword detection
                    text_lower = text.lower()
                    if text_lower.startswith("gemini"):
                        # Remove keyword and send rest as prompt
                        prompt = text[len("gemini"):].strip()
                        if prompt:
                            print(f"🎤 Gemini received voice prompt: {prompt}")
                            self.text_recognized.emit(prompt)
                        else:
                            print("⚠️ No prompt detected after keyword.")
                    else:
                        print("🔇 Ignored (no keyword).")

                except sr.UnknownValueError:
                    print("❌ Could not understand audio")
                except sr.RequestError as e:
                    print(f"⚠️ API error: {e}")
                except Exception as e:
                    print(f"⚠️ Unexpected error: {e}")
"""
import threading
import speech_recognition as sr
from PySide6.QtCore import QObject, Signal


class VoiceController(QObject):
    text_recognized = Signal(str)  # signal for Gemini

    def __init__(self, music_widget, gemini_handler):
        super().__init__()
        self.music_widget = music_widget
        self.gemini_handler = gemini_handler
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self._running = False
        self._thread = None

    def start_listening(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print("🎤 Voice controller started")

    def stop_listening(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join()
        print("🛑 Voice controller stopped")

    def _listen_loop(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            print("🎤 Voice controller is listening...")
            while self._running:
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=8)
                    text = self.recognizer.recognize_google(audio)
                    print(f"🗣️ You said: {text}")

                    text_lower = text.lower()

                    # === ✅ Gemini handling (must start with 'gemini') ===
                    if text_lower.startswith("gemini"):
                        command = text_lower[len("gemini"):].strip()
                        if command:
                            print(f"🤖 Gemini prompt: {command}")
                            self.text_recognized.emit(command)
                        else:
                            print("⚠️ No prompt detected after 'Gemini'.")
                        continue  # skip rest, handled by Gemini

                    # === ✅ Music handling ===
                    if "play music" in text_lower or "resume music" in text_lower:
                        print("🎶 Voice command: Play music")
                        self.music_widget.toggle_play()

                    elif "pause music" in text_lower or "stop music" in text_lower:
                        print("🎶 Voice command: Pause music")
                        self.music_widget.toggle_play()

                    elif "next song" in text_lower or "skip" in text_lower:
                        print("🎶 Voice command: Next song")
                        self.music_widget.next_track()

                    elif "previous song" in text_lower or "last song" in text_lower:
                        print("🎶 Voice command: Previous song")
                        self.music_widget.prev_track()

                    else:
                        print("🔇 Command not recognized as Gemini or music.")

                except sr.UnknownValueError:
                    print("❌ Could not understand audio")
                except sr.RequestError as e:
                    print(f"⚠️ API error: {e}")
                except Exception as e:
                    print(f"⚠️ Unexpected error: {e}")
