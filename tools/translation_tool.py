import re
from typing import Dict
from google import genai
import os

class TranslationTool:
    """
    Handles translation and language detection for English, Hindi, and Marathi.
    Provides offline dictionary fallbacks and online LLM translation when a Gemini client is available.
    """
    def __init__(self, gemini_client: genai.Client = None):
        self.client = gemini_client
        
        # Heuristic word list for simple language detection
        self.hindi_keywords = [
            r"madad", r"bachao", r"sahayata", r"chahiye", r"ho", r"gaya", r"hai", r"pareshani", 
            r"aag", r"katra", r"madat", r"bimar", r"chot", r"dard", r"aspatal", r"doctor"
        ]
        self.marathi_keywords = [
            r"madat", r"havya", r"ahe", r"vaachva", r"dhoka", r"bhiti", r"bhukamp", r"dukhapat", 
            r"traas", r"kharab", r"lok", r"karava", r"hvi", r"pahije", r"davaakhana", r"rughnalay"
        ]
        
        # Simple offline dictionary for bidirectional translations
        self.offline_dict: Dict[str, Dict[str, str]] = {
            "mujhe madad chahiye": {
                "en": "I need help",
                "mr": "मला मदत हवी आहे"
            },
            "bachao": {
                "en": "Save me / Rescue",
                "mr": "वाचवा"
            },
            "yahan aag lagi hai": {
                "en": "There is a fire here",
                "mr": "इथे आग लागली आहे"
            },
            "kya koi hai": {
                "en": "Is anyone there?",
                "mr": "इथे कोणी आहे का?"
            },
            "i need help": {
                "hi": "मुझे मदद चाहिए",
                "mr": "मला मदत हवी आहे"
            },
            "there is a fire here": {
                "hi": "यहाँ आग लगी है",
                "mr": "इथे आग लागली आहे"
            },
            "mala madat havi ahe": {
                "en": "I need help",
                "hi": "मुझे मदद चाहिए"
            },
            "vachva": {
                "en": "Save me / Rescue",
                "hi": "बचाओ"
            }
        }

    def detect_language(self, text: str) -> str:
        """
        Detects if input is in English ('en'), Hindi ('hi'), or Marathi ('mr').
        Uses regex keyword lists and defaults to 'en' if unsure.
        """
        text_lower = text.lower()
        
        # Check Devanagari script characters first
        # Hindi and Marathi use Devanagari script.
        # Check for specific Marathi characters like ळ (U+0933)
        if re.search(r"[\u0900-\u097F]", text):
            if "ळ" in text or "मला" in text or "आहे" in text or "हवी" in text:
                return "mr"
            return "hi"  # Default Devanagari to Hindi unless Marathi markers are found
            
        # Check Romanized (Hinglish/Marathlish) keywords
        marathi_hits = sum(1 for kw in self.marathi_keywords if re.search(r"\b" + kw + r"\b", text_lower))
        hindi_hits = sum(1 for kw in self.hindi_keywords if re.search(r"\b" + kw + r"\b", text_lower))
        
        if marathi_hits > hindi_hits and marathi_hits > 0:
            return "mr"
        elif hindi_hits > 0:
            return "hi"
            
        # Use LLM detection if online
        if self.client:
            try:
                response = self.client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=f"Respond with only a two letter code representing the language (en, hi, mr) of this text: '{text}'. If in doubt write en.",
                )
                detected = response.text.strip().lower()
                if detected in ["en", "hi", "mr"]:
                    return detected
            except Exception:
                pass
                
        return "en"

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translates text from source_lang to target_lang.
        Uses offline translation dict if exact matches are present, otherwise uses Gemini (or defaults to original text).
        """
        if source_lang == target_lang:
            return text
            
        text_clean = text.strip().lower().replace(".", "").replace("!", "").replace("?", "")
        
        # Try offline exact matches
        if text_clean in self.offline_dict and target_lang in self.offline_dict[text_clean]:
            return self.offline_dict[text_clean][target_lang]
            
        # Try online translation
        if self.client:
            try:
                lang_names = {"en": "English", "hi": "Hindi", "mr": "Marathi"}
                src = lang_names.get(source_lang, "English")
                tgt = lang_names.get(target_lang, "English")
                
                prompt = (
                    f"Translate the following text from {src} to {tgt}. "
                    "Maintain the emotional tone, emergency context, and critical advice structure. "
                    "Do not add any additional preamble, explanations, or meta-comments. Just output the translation.\n\n"
                    f"Text:\n{text}"
                )
                response = self.client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt,
                )
                translated = response.text.strip()
                if translated:
                    return translated
            except Exception as e:
                print(f"Online translation failed: {e}. Falling back to original text.")
                
        # Heuristic fallbacks for key terms if offline and not in dict
        if target_lang == "hi":
            return f"[अनुवाद: {text}]"
        elif target_lang == "mr":
            return f"[भाषांतर: {text}]"
        return text
