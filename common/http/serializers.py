from __future__ import annotations

from decimal import Decimal
from typing import Any

from rest_framework import serializers


class StrictIntegerField(serializers.IntegerField):
    def to_internal_value(self, data: Any) -> int:
        if isinstance(data, float):
            raise serializers.ValidationError(
                "Float values are not allowed. Use integer santim/milli-units."
            )
        if isinstance(data, str):
            try:
                if "." in data:
                    raise serializers.ValidationError(
                        "Float values are not allowed. Use integer santim/milli-units."
                    )
                return int(data)
            except ValueError:
                raise serializers.ValidationError("A valid integer is required.")
        return super().to_internal_value(data)


class SantimField(StrictIntegerField):
    default_error_messages = {
        **StrictIntegerField.default_error_messages,
        "min_value": "Price must be non-negative.",
        "max_value": "Price exceeds maximum allowed value.",
    }

    def __init__(self, **kwargs: Any):
        kwargs.setdefault("min_value", 0)
        kwargs.setdefault("max_value", 999_999_999_99)
        super().__init__(**kwargs)


class MilliUnitsField(StrictIntegerField):
    default_error_messages = {
        **StrictIntegerField.default_error_messages,
        "min_value": "Quantity must be non-negative.",
        "max_value": "Quantity exceeds maximum allowed value.",
    }

    def __init__(self, **kwargs: Any):
        kwargs.setdefault("min_value", 0)
        kwargs.setdefault("max_value", 1_000_000_000)
        super().__init__(**kwargs)


class DecimalSantimField(serializers.DecimalField):
    def __init__(self, **kwargs: Any):
        kwargs.setdefault("max_digits", 14)
        kwargs.setdefault("decimal_places", 2)
        kwargs.setdefault("min_value", Decimal("0"))
        super().__init__(**kwargs)

    def to_representation(self, value: Any) -> str:
        if isinstance(value, int):
            return f"{value / 100:.2f}"
        return super().to_representation(value)
