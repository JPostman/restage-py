class ReStageError(Exception):
    """Base error for the prototype runtime."""


class RegistrationError(ReStageError):
    """Raised when decorator metadata is invalid or duplicated."""


class ResolutionError(ReStageError):
    """Raised when a node, dependency, folder, or request cannot be resolved."""


class DependencyCycleError(ReStageError):
    """Raised when the dependency graph contains a cycle."""


class VerificationError(AssertionError, ReStageError):
    """Raised when response verification fails."""
