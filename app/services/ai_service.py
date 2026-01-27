# ==============================================================================
# AI SERVICE FOR CODE TRANSLATION AND CHAT
# ==============================================================================

import logging
from typing import Dict, List, Optional, Any
from openai import OpenAI
from openai import APIError, RateLimitError, APIConnectionError
from app.services.personalities import get_personality, PERSONALITIES
from app.services.socrates_handler import should_ask_question

# Configure logging
logger = logging.getLogger(__name__)

def get_openai_client() -> OpenAI:
    """
    Gets an OpenAI client instance.
    
    Returns:
        OpenAI client instance
    """
    api_key: Optional[str] = None

    # Try to get API key from Streamlit session_state if available
    try:
        import streamlit as st
        api_key = st.session_state.get("user_api_key")
    except Exception:
        # Not running inside Streamlit – no session_state available
        api_key = None

    if not api_key:
        # No API key provided – instruct user to set it in the UI
        raise ValueError(
            "Brak klucza OpenAI API. Wprowadź swój klucz w panelu bocznym aplikacji."
        )

    return OpenAI(api_key=api_key)

MODEL_PRICINGS = {
    "gpt-4o": {
        "input_tokens": 5.00 / 1_000_000,
        "output_tokens": 15.00 / 1_000_000,
    },
    "gpt-4o-mini": {
        "input_tokens": 0.150 / 1_000_000,
        "output_tokens": 0.600 / 1_000_000,
    }
}

DEFAULT_MODEL = "gpt-4o"
USD_TO_PLN = 3.69

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def extract_usage_data(response) -> Dict[str, int]:
    """Extracts usage data from OpenAI API response."""
    if response.usage:
        return {
            "completion_tokens": response.usage.completion_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
            "total_tokens": response.usage.total_tokens,
        }
    return {}

def make_api_call(func, *args, max_retries: int = 3, **kwargs) -> Any:
    """
    Makes an API call with retry logic and error handling.
    
    Args:
        func: The API function to call
        *args: Positional arguments for the function
        max_retries: Maximum number of retry attempts
        **kwargs: Keyword arguments for the function
    
    Returns:
        The API response
    
    Raises:
        APIError: If the API call fails after all retries
    """
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                import time
                time.sleep(wait_time)
            else:
                logger.error(f"Rate limit error after {max_retries} attempts: {e}")
                raise
        except APIConnectionError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"Connection error, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                import time
                time.sleep(wait_time)
            else:
                logger.error(f"Connection error after {max_retries} attempts: {e}")
                raise
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in API call: {e}")
            raise

def calculate_cost(usage: Dict[str, int], model: str = DEFAULT_MODEL) -> float:
    """
    Calculates cost based on token usage.
    
    Args:
        usage: Dictionary with token usage data (prompt_tokens, completion_tokens, total_tokens)
        model: Model name to use for pricing
    
    Returns:
        Cost in USD
    """
    pricing = MODEL_PRICINGS.get(model, MODEL_PRICINGS[DEFAULT_MODEL])
    input_cost = usage.get("prompt_tokens", 0) * pricing["input_tokens"]
    output_cost = usage.get("completion_tokens", 0) * pricing["output_tokens"]
    return input_cost + output_cost

def chat_completion(
    messages: List[Dict[str, str]], 
    personality: str = "default", 
    model: str = DEFAULT_MODEL, 
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Sends a chat completion request to OpenAI.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
        personality: Personality name or custom personality text
        model: Model name to use
        conversation_history: Optional conversation history for Socrates personality handling
    
    Returns:
        Dictionary with 'content' and 'usage' keys
    
    Raises:
        APIError: If the API call fails
    """
    try:
        # If personality is a predefined name, get it from dictionary; otherwise use it as-is (custom personality)
        if personality in PERSONALITIES:
            personality_text = get_personality(personality)
            personality_name = personality
        else:
            # Custom personality text passed directly
            personality_text = personality
            personality_name = None  # Not a predefined personality
        
        system_message = {"role": "system", "content": personality_text}
        full_messages = [system_message] + messages
        
        logger.debug(f"Making chat completion request with model {model}, personality {personality_name or 'custom'}")
        
        client = get_openai_client()
        response = make_api_call(
            client.chat.completions.create,
            model=model,
            messages=full_messages
        )
        
        usage = extract_usage_data(response)
        content = response.choices[0].message.content
        
        # Handle Socrates personality (only for predefined "socrates" personality)
        if personality_name == "socrates" and conversation_history:
            user_message = messages[-1]["content"] if messages else ""
            if not should_ask_question(user_message, conversation_history):
                # User said "nie wiem" three times, modify system message to give direct answer
                logger.info("User said 'nie wiem' three times, providing direct answer")
                system_message = {
                    "role": "system",
                    "content": "Użytkownik powiedział 'nie wiem' trzy razy z rzędu. Teraz udziel bezpośredniej, szczegółowej odpowiedzi na jego pytanie."
                }
                full_messages = [system_message] + messages
                client = get_openai_client()
                response = make_api_call(
                    client.chat.completions.create,
                    model=model,
                    messages=full_messages
                )
                usage = extract_usage_data(response)
                content = response.choices[0].message.content
        
        return {
            "content": content,
            "usage": usage
        }
    except Exception as e:
        logger.error(f"Error in chat_completion: {e}")
        raise

def translate_code(
    code: str, 
    source_language: str, 
    target_language: str, 
    level: str = "simple", 
    model: str = DEFAULT_MODEL, 
    lang: str = "pl"
) -> Dict[str, Any]:
    """
    Converts code from one programming language to another.
    
    Args:
        code: Source code to translate
        source_language: Source programming language
        target_language: Target programming language
        level: "simple" for simple/general conversion, "advanced" for detailed/beginner-friendly
        model: Model name to use
        lang: "pl" for Polish, "en" for English
    
    Returns:
        Dictionary with 'translated_code' and 'usage' keys
    
    Raises:
        APIError: If the API call fails
    """
    try:
        if lang == "en":
            if level == "simple":
                prompt = f"""Translate the following code from {source_language} to {target_language}.
Provide only the translated code without additional explanations.

Source code:
```{source_language}
{code}
```"""
            else:  # advanced
                prompt = f"""Translate the following code from {source_language} to {target_language} and explain in detail:
1. Each line of code
2. How each part works
3. Differences between languages
4. Best practices

Source code:
```{source_language}
{code}
```"""
        else:  # Polish
            if level == "simple":
                prompt = f"""Przetłumacz poniższy kod z {source_language} na {target_language}.
Podaj tylko przetłumaczony kod bez dodatkowych wyjaśnień.

Kod źródłowy:
```{source_language}
{code}
```"""
            else:  # advanced
                prompt = f"""Przetłumacz poniższy kod z {source_language} na {target_language} i wyjaśnij szczegółowo:
1. Każdą linię kodu
2. Jak działa każda część
3. Różnice między językami
4. Najlepsze praktyki

Kod źródłowy:
```{source_language}
{code}
```"""
        
        messages = [{"role": "user", "content": prompt}]
        
        logger.debug(f"Translating code from {source_language} to {target_language} (level: {level})")
        
        client = get_openai_client()
        response = make_api_call(
            client.chat.completions.create,
            model=model,
            messages=messages
        )
        
        usage = extract_usage_data(response)
        
        return {
            "translated_code": response.choices[0].message.content,
            "usage": usage
        }
    except Exception as e:
        logger.error(f"Error in translate_code: {e}")
        raise

def explain_code_from_image(
    image_base64: str, 
    level: str = "simple", 
    model: str = DEFAULT_MODEL, 
    use_voice: bool = False, 
    lang: str = "pl"
) -> Dict[str, Any]:
    """
    Explains code from an image.
    
    Args:
        image_base64: Base64-encoded image string
        level: "simple" for simple explanation, "advanced" for detailed explanation
        model: Model name to use
        use_voice: if True, response should be suitable for text-to-speech
        lang: "pl" for Polish, "en" for English
    
    Returns:
        Dictionary with 'explanation' and 'usage' keys
    
    Raises:
        APIError: If the API call fails
    """
    try:
        if lang == "en":
            if level == "simple":
                prompt = "Explain briefly and generally what the code in this image does."
            else:  # advanced
                prompt = """Analyze the code in this image in detail and provide:
1. Line-by-line explanation
2. Time and space complexity analysis (Big O notation)
3. Potential security issues and bugs
4. Optimization suggestions
5. Generate at least 2 alternative implementations of the same functionality (minimum 2, preferably 3)
6. Compare all versions: pros/cons, performance, readability, maintainability
7. Design patterns used or that could be applied
8. Best practices and recommendations
9. Context and use cases where each version would be better

Format your response with clear sections. For alternative implementations, use code blocks with labels like "Alternative 1:", "Alternative 2:", "Alternative 3:", etc. Always provide at least 2 alternatives."""
            
            if use_voice:
                prompt += " Respond in a way suitable for reading aloud - use simple language and short sentences."
        else:  # Polish
            if level == "simple":
                prompt = "Wyjaśnij krótko i ogólnie, co robi kod na tym obrazku."
            else:  # advanced
                prompt = """Przeanalizuj kod na tym obrazku szczegółowo i przedstaw:
1. Wyjaśnienie linia po linii
2. Analizę złożoności czasowej i pamięciowej (notacja Big O)
3. Potencjalne problemy bezpieczeństwa i błędy
4. Sugestie optymalizacji
5. Wygeneruj minimum 2 alternatywne implementacje tej samej funkcjonalności (minimum 2, najlepiej 3)
6. Porównaj wszystkie wersje: zalety/wady, wydajność, czytelność, utrzymanie
7. Wzorce projektowe użyte lub które można zastosować
8. Najlepsze praktyki i rekomendacje
9. Kontekst i przypadki użycia, gdzie każda wersja byłaby lepsza

Sformatuj odpowiedź z wyraźnymi sekcjami. Dla alternatywnych implementacji użyj bloków kodu z etykietami jak "Alternatywa 1:", "Alternatywa 2:", "Alternatywa 3:", itd. Zawsze podaj minimum 2 alternatywy."""
            
            if use_voice:
                prompt += " Odpowiedz w sposób odpowiedni do odczytania na głos - użyj prostego języka i krótkich zdań."
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}",
                            "detail": "high"
                        }
                    }
                ]
            }
        ]
        
        logger.debug(f"Explaining code from image (level: {level}, use_voice: {use_voice})")
        
        client = get_openai_client()
        response = make_api_call(
            client.chat.completions.create,
            model=model,
            messages=messages
        )
        
        usage = extract_usage_data(response)
        
        return {
            "explanation": response.choices[0].message.content,
            "usage": usage
        }
    except Exception as e:
        logger.error(f"Error in explain_code_from_image: {e}")
        raise

def transcribe_audio(audio_file: Any) -> str:
    """
    Transcribes audio to text using Whisper.
    
    Args:
        audio_file: Audio file object to transcribe
        api_key: Optional API key to use
    
    Returns:
        Transcribed text
    
    Raises:
        APIError: If the API call fails
    """
    try:
        logger.debug("Transcribing audio file")
        client = get_openai_client()
        transcript = make_api_call(
            client.audio.transcriptions.create,
            file=audio_file,
            model="whisper-1"
        )
        return transcript.text
    except Exception as e:
        logger.error(f"Error in transcribe_audio: {e}")
        raise

def text_to_speech(text: str, voice: str = "alloy", max_length: int = 4096) -> bytes:
    """
    Converts text to speech. Truncates text if it exceeds max_length.
    
    Args:
        text: Text to convert to speech
        voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
        max_length: Maximum text length (OpenAI TTS API limit is 4096 characters)
        api_key: Optional API key to use
    
    Returns:
        Audio content as bytes
    
    Raises:
        APIError: If the API call fails
    """
    try:
        # OpenAI TTS API has a limit of 4096 characters
        if len(text) > max_length:
            logger.warning(f"Text length ({len(text)}) exceeds max_length ({max_length}), truncating")
            text = text[:max_length-3] + "..."
        
        logger.debug(f"Converting text to speech with voice {voice}")
        client = get_openai_client()
        response = make_api_call(
            client.audio.speech.create,
            model="tts-1",
            voice=voice,
            input=text
        )
        return response.content
    except Exception as e:
        logger.error(f"Error in text_to_speech: {e}")
        raise

