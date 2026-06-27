import os
from gtts import gTTS
import speech_recognition as sr
from typing import Optional

class VoiceTool:
    """
    Handles speech-to-text (STT) and text-to-speech (TTS) conversion.
    Supports speech synthesis mapped to nearest supported voice for 28 languages.
    """
    def __init__(self, temp_dir: str = "temp_audio"):
        self.temp_dir = temp_dir
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def text_to_speech(self, text: str, lang: str = "en") -> Optional[str]:
        """
        Converts text to an MP3 audio file using the selected language code or best fallback.
        """
        if not text:
            return None
            
        clean_text = text.replace("**", "").replace("*", "").replace("#", "").replace("`", "")
        
        # Standardize language code (e.g., 'en-US' -> 'en')
        lang_code = lang.lower().split("-")[0]
        
        # Mapping 28 languages to gTTS codes (with intelligent fallback to close phonetic matches)
        gtts_map = {
            "en": "en", "hi": "hi", "mr": "mr", "bn": "bn", "te": "te",
            "ta": "ta", "gu": "gu", "kn": "kn", "ml": "ml", "pa": "pa",
            "ur": "ur", "or": "hi",  # Odia fallback to Hindi
            "as": "bn",  # Assamese fallback to Bengali
            "ne": "ne", "sa": "hi",  # Sanskrit fallback to Hindi
            "es": "es", "fr": "fr", "de": "de", "it": "it", "pt": "pt",
            "zh": "zh", "ja": "ja", "ko": "ko", "ar": "ar", "ru": "ru",
            "tr": "tr", "id": "id", "vi": "vi"
        }
        
        gtts_lang = gtts_map.get(lang_code, "en")
        
        try:
            tts = gTTS(text=clean_text, lang=gtts_lang, slow=False)
            filename = f"tts_{hash(clean_text) & 0xffffffff}.mp3"
            filepath = os.path.join(self.temp_dir, filename)
            tts.save(filepath)
            return filepath
        except Exception as e:
            print(f"TTS conversion failed for lang {lang} ({gtts_lang}): {e}")
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
