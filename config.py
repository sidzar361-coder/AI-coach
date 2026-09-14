import os


GEMINI_MODEL = "gemini-3.6-flash"


def get_gemini_api_key():
    """Return the configured Gemini key without exposing its value."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not configured.")
    return api_key


def create_gemini_client():
    """Create a Gemini client for one complete request lifecycle."""
    from google import genai

    return genai.Client(api_key=get_gemini_api_key())


def create_gemini_interaction(prompt):
    """Run one interaction while its client is alive, then close that client."""
    client = create_gemini_client()
    try:
        return client.interactions.create(model=GEMINI_MODEL, input=prompt)
    finally:
        close = getattr(client, "close", None)
        if close is not None:
            close()