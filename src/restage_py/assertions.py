from __future__ import annotations

from dataclasses import dataclass, field

from .errors import VerificationError
from .model import HttpResponse


@dataclass(slots=True)
class ReStageAssert:
    """Hard and soft assertions scoped to one invocation."""

    response: HttpResponse | None
    _soft_mode: bool = False
    _errors: list[str] = field(default_factory=list)

    def soft(self, enabled: bool = True) -> "ReStageAssert":
        return ReStageAssert(
            response=self.response,
            _soft_mode=enabled,
            _errors=self._errors,
        )

    def status_code(self, expected: int) -> "ReStageAssert":
        actual = self.response.status_code if self.response else None
        if actual != expected:
            self._fail_or_collect(
                f"Expected status code {expected}, but received {actual}."
            )
        return self

    def is_true(self, condition: bool, message: str = "Condition is false.") -> "ReStageAssert":
        if not condition:
            self._fail_or_collect(message)
        return self

    def fail(self, message: str) -> None:
        self._fail_or_collect(message)

    def verify(self) -> None:
        if self._errors:
            messages = list(self._errors)
            self._errors.clear()
            raise VerificationError("\n".join(messages))

    def _fail_or_collect(self, message: str) -> None:
        if self._soft_mode:
            self._errors.append(message)
            return
        raise VerificationError(message)
