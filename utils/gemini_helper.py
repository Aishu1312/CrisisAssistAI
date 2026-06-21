import time
import re

def safe_generate_content(client, model, contents, config=None, max_retries=3):
    """
    Safely calls client.models.generate_content with exponential backoff on 429 rate limits.
    """
    for attempt in range(max_retries):
        try:
            if config:
                return client.models.generate_content(model=model, contents=contents, config=config)
            return client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()
            if is_rate_limit and attempt < max_retries - 1:
                sleep_time = 2.0 * (attempt + 1)
                # Try to parse retryDelay from API error
                match = re.search(r"retryDelay': '(\d+)s'", err_str)
                if not match:
                    match = re.search(r"retry in ([\d.]+)s", err_str, re.IGNORECASE)
                if match:
                    sleep_time = float(match.group(1)) + 1.0
                
                print(f"Gemini API rate limited (429) on attempt {attempt + 1}. Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                raise e
