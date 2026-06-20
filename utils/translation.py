from utils.language_loader import LanguageLoader
from typing import Dict

class TranslationManager:
    """
    Manages user UI translation lookups across 28 supported languages.
    Uses caching and fallback logic to guarantee key safety.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(TranslationManager, cls).__new__(cls, *args, **kwargs)
            cls._instance.loader = LanguageLoader()
        return cls._instance

    def get(self, key: str, lang_code: str) -> str:
        """
        Translates a UI key into the target language.
        Falls back to English if the key is missing from the target dictionary.
        """
        labels = self.loader.get_labels(lang_code)
        
        # Check if key is present in requested language
        if key in labels:
            return labels[key]
            
        # Fallback to English
        english_labels = self.loader.get_labels("en")
        return english_labels.get(key, key)

    def get_supported_languages(self) -> Dict[str, str]:
        """Returns map of language codes to their full display names."""
        return {
            "en": "English", "hi": "Hindi", "mr": "Marathi", "bn": "Bengali", "te": "Telugu",
            "ta": "Tamil", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam", "pa": "Punjabi",
            "ur": "Urdu", "or": "Odia", "as": "Assamese", "ne": "Nepali", "sa": "Sanskrit",
            "es": "Spanish", "fr": "French", "de": "German", "it": "Italian", "pt": "Portuguese",
            "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "ru": "Russian",
            "tr": "Turkish", "id": "Indonesian", "vi": "Vietnamese"
        }
