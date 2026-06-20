import os
import json
from typing import Dict, Any

class LanguageLoader:
    """
    Loads JSON translation files for the 28 supported languages.
    Falls back to English if a language file is missing or corrupted.
    """
    def __init__(self, translations_dir: str = "translations"):
        self.translations_dir = translations_dir
        self.cache: Dict[str, Dict[str, str]] = {}
        # Ensure we always load English as standard fallback
        self.fallback_lang = "en"
        self._load_lang_file(self.fallback_lang)

    def _load_lang_file(self, lang_code: str) -> Dict[str, str]:
        """Loads a single language JSON file into cache."""
        if lang_code in self.cache:
            return self.cache[lang_code]
            
        filepath = os.path.join(self.translations_dir, f"{lang_code}.json")
        if not os.path.exists(filepath):
            # Fallback to English if file doesn't exist
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
        """Returns the dictionary of labels for the selected language code."""
        # Convert full language names to codes if needed
        clean_code = lang_code.lower().strip()[:2]
        
        # Support full name matching
        lang_map = {
            "en": "en", "hi": "hi", "mr": "mr", "be": "bn", "te": "te", "ta": "ta", "gu": "gu", 
            "ka": "kn", "ma": "ml", "pu": "pa", "ur": "ur", "od": "or", "as": "as", "ne": "ne", 
            "sa": "sa", "es": "es", "fr": "fr", "de": "de", "it": "it", "po": "pt", "ch": "zh", 
            "ja": "ja", "ko": "ko", "ar": "ar", "ru": "ru", "tu": "tr", "in": "id", "vi": "vi"
        }
        
        resolved_code = lang_map.get(clean_code, self.fallback_lang)
        return self._load_lang_file(resolved_code)
