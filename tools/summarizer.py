from google import genai
from typing import List

class Summarizer:
    """
    Summarizes dense instructions or resource texts into clear, actionable bullet points.
    Critical for helping users read instructions rapidly during high-stress crises.
    """
    def __init__(self, gemini_client: genai.Client = None):
        self.client = gemini_client

    def summarize(self, text: str) -> str:
        """
        Summarizes input text into a bulleted checklist of 3-5 immediate steps.
        """
        if not text:
            return ""

        # Online LLM-based summarization
        if self.client:
            try:
                prompt = (
                    "Summarize the following emergency guidelines into a checklist of "
                    "exactly 3 to 5 clear, actionable, short steps. Use Markdown bullet points (-). "
                    "Prioritize life safety first. Do not add intro or outro text.\n\n"
                    f"Text to summarize:\n{text}"
                )
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                )
                summary = response.text.strip()
                if summary:
                    return summary
            except Exception as e:
                print(f"Online summarizer failed: {e}. Falling back to heuristic summary.")

        # Offline heuristic summarizer
        return self._heuristic_summary(text)

    def _heuristic_summary(self, text: str) -> str:
        """
        Heuristic offline summarizer that parses lines and extracts action verbs or bullet lists.
        """
        lines = text.split("\n")
        action_lines = []
        
        # Action keywords indicating immediate instructions
        action_verbs = [
            "stay", "move", "evacuate", "call", "seek", "run", "cover", "hide", "stop", "check",
            "avoid", "keep", "find", "use", "do not", "don't", "bachao", "jao", "dekhain", "karin"
        ]
        
        for line in lines:
            line_clean = line.strip().lstrip("-*•1234567890. ")
            if not line_clean:
                continue
                
            line_lower = line_clean.lower()
            # If line starts with or contains action verbs and is reasonably short, capture it
            if any(line_lower.startswith(verb) for verb in action_verbs) or len(line_clean.split()) < 15:
                action_lines.append(f"- {line_clean}")
                if len(action_lines) >= 4:
                    break
                    
        # Fallback if no lines matched heuristics
        if not action_lines:
            # Just take the first few non-empty lines
            for line in lines:
                line_clean = line.strip()
                if line_clean and len(line_clean) > 10:
                    action_lines.append(f"- {line_clean}")
                    if len(action_lines) >= 3:
                        break
                        
        return "\n".join(action_lines)
