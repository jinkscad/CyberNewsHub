"""
ML-based article categorization using zero-shot classification.
Uses a pre-trained model to categorize articles more accurately than keywords.
Model loads lazily on first use to avoid blocking startup.
"""

import os

# Lazy load everything - don't import transformers until needed
_classifier = None
_model_loaded = False
_load_attempted = False


def get_classifier():
    """Lazy load the zero-shot classifier on first use."""
    global _classifier, _model_loaded, _load_attempted

    if _load_attempted:
        return _classifier

    _load_attempted = True

    try:
        # Only import when actually needed
        from transformers import pipeline
        import warnings
        warnings.filterwarnings('ignore')

        print("Loading ML categorization model (first use, may take a minute)...")

        # Use a smaller model for faster loading
        # typeform/distilbert-base-uncased-mnli is smaller and faster
        _classifier = pipeline(
            "zero-shot-classification",
            model="typeform/distilbert-base-uncased-mnli",
            device=-1  # CPU
        )

        print("ML model loaded successfully!")
        _model_loaded = True
        return _classifier

    except Exception as e:
        print(f"ML model unavailable: {e}")
        print("Using keyword-based categorization instead")
        _classifier = None
        return None


def categorize_with_ml(title, description):
    """
    Categorize article using zero-shot classification.

    Args:
        title: Article title
        description: Article description/summary

    Returns:
        tuple: (category, confidence) or (None, 0) if ML unavailable
    """
    classifier = get_classifier()

    if classifier is None:
        return None, 0

    # Combine title and description for better context
    text = f"{title}. {description or ''}"[:512]

    if not text.strip():
        return None, 0

    try:
        result = classifier(
            text,
            candidate_labels=["news", "alert", "research", "event"],
            hypothesis_template="This is a cybersecurity {}.",
            multi_label=False
        )

        # Map to proper case
        label_map = {
            "news": "News",
            "alert": "Alert",
            "research": "Research",
            "event": "Event"
        }

        top_label = result['labels'][0]
        confidence = result['scores'][0]
        category = label_map.get(top_label, 'News')

        return category, confidence

    except Exception as e:
        print(f"ML categorization error: {e}")
        return None, 0


def preload_model():
    """Call this to load model in background thread."""
    import threading
    thread = threading.Thread(target=get_classifier, daemon=True)
    thread.start()
