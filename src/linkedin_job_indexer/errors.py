class JobIndexerError(RuntimeError):
    """Base error for expected indexer failures."""


class ConfigError(ValueError):
    """Raised when configuration is invalid."""


class ExtractionError(JobIndexerError):
    """Raised when LinkedIn cannot be fetched reliably."""


class ExtractionBlockedError(ExtractionError):
    """Raised when LinkedIn returns a block or challenge page."""


class ParsingError(JobIndexerError):
    """Raised when expected LinkedIn content cannot be parsed."""
