import os
from gtts import gTTS
import speech_recognition as sr
from typing import Optional

class VoiceTool:
    """
    Handles speech-to-text (STT) and text-to-speech (TTS) conversion.
    Saves TTS audio files into a temporary directory for local browser playbacks.
    """
    def __init__(self, temp_dir: str = "temp_audio"):
        self.temp_dir = temp_dir
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def text_to_speech(self, text: str, lang: str = "en") -> Optional[str]:
        """
        Converts text to an MP3 audio file.
        Args:
            text: The text string to read.
            lang: 'en' for English, 'hi' for Hindi, or 'mr' for Marathi.
        Returns:
            The file path of the generated audio file, or None if failed.
        """
        if not text:
            return None
            
        # Clean text slightly (remove markdown styling like ** or # for clearer TTS)
        clean_text = text.replace("**", "").replace("*", "").replace("#", "").replace("`", "")
        
        # Mapping standard language codes to gTTS tags
        gtts_lang = "en"
        if lang == "hi":
            gtts_lang = "hi"
        elif lang == "mr":
            gtts_lang = "mr"
            
        try:
            tts = gTTS(text=clean_text, lang=gtts_lang, slow=False)
            filename = f"tts_{hash(clean_text) & 0xffffffff}.mp3"
            filepath = os.path.join(self.temp_dir, filename)
            
            # Save the generated audio file
            tts.save(filepath)
            return filepath
        except Exception as e:
            print(f"TTS conversion failed: {e}")
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

    def get_voice_commands_map(self, phrase: str) -> str:
        """
        Optional helper mapping common spoken keywords to typical requests.
        """
        phrase_clean = phrase.lower().strip()
        if "fire" in phrase_clean or "aag" in phrase_clean:
            return "Fire emergency near me"
        if "doctor" in phrase_clean or "hospital" in phrase_clean or "madad" in phrase_clean:
            return "Medical help needed"
        return phrase
