import os
import json
from typing import Dict, Any

class LanguageManager:
    """
    Manages loading, caching, and mapping of translation files for 28 languages.
    Provides UI translations and resolves lang codes robustly.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LanguageManager, cls).__new__(cls, *args, **kwargs)
            # Find translations dir relative to this file
            cls._instance.translations_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                "translations"
            )
            cls._instance.cache = {}
            cls._instance.fallback_lang = "en"
            cls._instance.loader = cls._instance
            cls._instance._load_lang_file(cls._instance.fallback_lang)
        return cls._instance

    def __init__(self):
        # Clear cache to force reloading from disk on each app rerun/reload
        self.cache.clear()
        self._load_lang_file(self.fallback_lang)

    def _load_lang_file(self, lang_code: str) -> Dict[str, str]:
        if lang_code in self.cache:
            return self.cache[lang_code]

        filepath = os.path.join(self.translations_dir, f"{lang_code}.json")
        if not os.path.exists(filepath):
            if lang_code == self.fallback_lang:
                return {}
            return self._load_lang_file(self.fallback_lang)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.cache[lang_code] = data
                return data
        except Exception as e:
            print(f"Error loading language file {lang_code}: {e}")
            if lang_code == self.fallback_lang:
                return {}
            return self._load_lang_file(self.fallback_lang)

    def get_labels(self, lang_code: str) -> Dict[str, str]:
        clean_code = lang_code.lower().strip()[:2]
        supported = [
            "en", "hi", "mr", "bn", "te", "ta", "gu", "kn", "ml", "pa", "ur", "or", "as", 
            "ne", "sa", "es", "fr", "de", "it", "pt", "zh", "ja", "ko", "ar", "ru", "tr", 
            "id", "vi"
        ]
        resolved_code = clean_code if clean_code in supported else self.fallback_lang
        return self._load_lang_file(resolved_code)

    def get(self, key: str, lang_code: str) -> str:
        labels = self.get_labels(lang_code)
        if key in labels:
            return labels[key]
        english_labels = self.get_labels(self.fallback_lang)
        return english_labels.get(key, key)

    def get_supported_languages(self) -> Dict[str, str]:
        return {
            "en": "English", "hi": "Hindi", "mr": "Marathi", "bn": "Bengali", "te": "Telugu",
            "ta": "Tamil", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam", "pa": "Punjabi",
            "ur": "Urdu", "or": "Odia", "as": "Assamese", "ne": "Nepali", "sa": "Sanskrit",
            "es": "Spanish", "fr": "French", "de": "German", "it": "Italian", "pt": "Portuguese",
            "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "ru": "Russian",
            "tr": "Turkish", "id": "Indonesian", "vi": "Vietnamese"
        }
