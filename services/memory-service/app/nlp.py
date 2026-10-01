"""
Single spaCy entry point.

The model is a pinned install-time dependency (see requirements.txt). It is
never downloaded at runtime: a missing model is a deployment error and fails
with an actionable message.
"""

from functools import lru_cache

import spacy
from spacy.tokens import Doc

from app.config import settings

# Parsing is a pure function of the text for a fixed model, so a bounded
# process-wide cache is safe. It removes repeated parses of the same memory
# across classifier, contradiction detector, context and diversity stages.
PARSE_CACHE_SIZE = 4096


class NLPModelUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_nlp():
    model = settings.spacy_model
    try:
        return spacy.load(model)
    except OSError as exc:
        raise NLPModelUnavailable(
            f"spaCy model '{model}' is not installed. Install the pinned model with "
            f"'pip install -r services/memory-service/requirements.txt' "
            f"(or 'python -m spacy download {model}'). "
            f"AutoMemory OS never downloads models at runtime."
        ) from exc


@lru_cache(maxsize=PARSE_CACHE_SIZE)
def parse_text(text: str) -> Doc:
    """Parsed spaCy Doc for text. Callers must treat the Doc as read-only."""
    return get_nlp()(text)
