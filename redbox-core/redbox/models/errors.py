class AIError(Exception):
    """Basic error class for problems with the AI components."""


class QuestionLengthError(AIError):
    """Question length exceeds context window."""


class NoDocumentSelected(AIError):
    """No documents selected."""
