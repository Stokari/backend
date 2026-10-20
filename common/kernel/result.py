from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=Exception)


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_err(self) -> E:
        raise RuntimeError("Called unwrap_err on Ok")

    def map(self, fn: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return fn(self.value)

    def and_then(self, fn: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return fn(self.value)

    def map_err(self, fn: Callable[[E], E]) -> "Result[T, E]":
        return self


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> T:
        raise self.error

    def unwrap_err(self) -> E:
        return self.error

    def map(self, fn: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return Err(self.error)

    def and_then(self, fn: Callable[[T], "Result[U, E]"]) -> "Result[U, E]":
        return Err(self.error)

    def map_err(self, fn: Callable[[E], E]) -> "Result[T, E]":
        return Err(fn(self.error))


Result = Ok[T] | Err[E]

U = TypeVar("U")


def ok(value: T) -> Ok[T]:
    return Ok(value)


def err(error: E) -> Err[E]:
    return Err(error)


def from_optional(value: T | None, error: E) -> Result[T, E]:
    if value is None:
        return Err(error)
    return Ok(value)


def from_bool(condition: bool, error: E) -> Result[None, E]:
    if condition:
        return Ok(None)
    return Err(error)
