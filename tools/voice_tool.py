import os
from gtts import gTTS
import speech_recognition as sr
from typing import Optional

class VoiceTool:
    """
    Handles speech-to-text (STT) and text-to-speech (TTS) conversion.
    Supports speech synthesis across multi-language ISO codes.
    """
    def __init__(self, temp_dir: str = "temp_audio"):
        self.temp_dir = temp_dir
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def text_to_speech(self, text: str, lang: str = "en") -> Optional[str]:
        """
        Converts text to an MP3 audio file.
        """
        if not text:
            return None
            
        clean_text = text.replace("**", "").replace("*", "").replace("#", "").replace("`", "")
        
        # Support common gTTS language tags
        gtts_lang = lang.lower().split("-")[0]
        
        try:
            tts = gTTS(text=clean_text, lang=gtts_lang, slow=False)
            filename = f"tts_{hash(clean_text) & 0xffffffff}.mp3"
            filepath = os.path.join(self.temp_dir, filename)
            tts.save(filepath)
            return filepath
        except Exception as e:
            print(f"TTS conversion failed for lang {lang}: {e}")
            # Fallback to English TTS if the specific language fails
            try:
                tts = gTTS(text=clean_text, lang="en", slow=False)
                filename = f"tts_{hash(clean_text) & 0xffffffff}_en_fallback.mp3"
                filepath = os.path.join(self.temp_dir, filename)
                tts.save(filepath)
                return filepath
            except Exception:
                return None

    def speech_to_text(self, audio_file_path: str) -> Optional[str]:
        """
        Converts an audio file (.wav or .mp3) to text using Google Speech Recognition.
        """
        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(audio_file_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)
                return text
        except Exception as e:
            print(f"STT speech recognition error: {e}")
            return None
