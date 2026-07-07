class LoaderError(Exception):
    """Base exception for document loading failures."""


class UnsupportedDocumentTypeError(LoaderError):
    """Raised when no loader exists for the input document type."""


class DocumentLoadError(LoaderError):
    """Raised when a supported document cannot be loaded."""


class OCRNotAvailableError(DocumentLoadError):
    """Raised when Tesseract OCR is not available or not configured."""
