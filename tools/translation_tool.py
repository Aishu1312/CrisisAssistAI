import re
from typing import Dict
from google import genai
import os
from utils.gemini_helper import safe_generate_content

class TranslationTool:
    """
    Handles translation and language detection for 28 supported languages using Gemini.
    """
    def __init__(self, gemini_client: genai.Client = None):
        self.client = gemini_client
        
        # Languages map
        self.languages = {
            "en": "English", "hi": "Hindi", "mr": "Marathi", "bn": "Bengali", "te": "Telugu",
            "ta": "Tamil", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam", "pa": "Punjabi",
            "ur": "Urdu", "or": "Odia", "as": "Assamese", "ne": "Nepali", "sa": "Sanskrit",
            "es": "Spanish", "fr": "French", "de": "German", "it": "Italian", "pt": "Portuguese",
            "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "ru": "Russian",
            "tr": "Turkish", "id": "Indonesian", "vi": "Vietnamese"
        }

    def detect_language(self, text: str) -> str:
        """
        Detects the ISO code of the language of the query.
        """
        # Devanagari script checks for Marathi / Hindi
        if re.search(r"[\u0900-\u097F]", text):
            if any(w in text for w in ["ळ", "मला", "आहे", "हवी", "काय", "नाव"]):
                return "mr"
            return "hi"
            
        if self.client:
            try:
                prompt = (
                    "Analyze the following text and detect its language. Respond ONLY with a standard "
                    "two-letter ISO language code (e.g. en, hi, mr, es, fr, zh, ar) in lowercase. Do not write anything else.\n\n"
                    f"Text: '{text}'"
                )
                response = safe_generate_content(
                    self.client,
                    model="gemini-flash-latest",
                    contents=prompt,
                )
                detected = response.text.strip().lower()
                if detected in self.languages:
                    return detected
            except Exception:
                pass
                
        return "en"

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translates text from source_lang to target_lang using Gemini.
        """
        src_clean = source_lang.lower().strip()[:2]
        tgt_clean = target_lang.lower().strip()[:2]
        
        if src_clean == tgt_clean:
            return text
            
        if self.client:
            try:
                src = self.languages.get(src_clean, "English")
                tgt = self.languages.get(tgt_clean, "English")
                
                prompt = (
                    f"Translate the following text from {src} to {tgt}. "
                    "Preserve all emergency guidelines, bullet numbers, safety warnings, and address structures. "
                    "Do not write any intro, explanations, or meta-comments. Just output the translation.\n\n"
                    f"Text:\n{text}"
                )
                response = safe_generate_content(
                    self.client,
                    model="gemini-flash-latest",
                    contents=prompt,
                )
                translated = response.text.strip()
                if translated:
                    return translated
            except Exception as e:
                print(f"Online translation failed: {e}. Falling back to original text.")
                
        tgt_name = self.languages.get(tgt_clean, "English")
        return f"[{tgt_name} Translation]: {text}"
