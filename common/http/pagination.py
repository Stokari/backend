from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from rest_framework.pagination import BasePagination
from rest_framework.request import Request
from rest_framework.response import Response

T = TypeVar("T")


class CursorPagination(BasePagination, Generic[T]):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_at"
    cursor_query_param = "cursor"

    def paginate_queryset(
        self, queryset: Sequence[T], request: Request, view=None
    ) -> list[T] | None:
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        cursor = request.query_params.get(self.cursor_query_param)
        if cursor:
            try:
                queryset = self.apply_cursor(queryset, cursor)
            except ValueError:
                pass

        queryset = queryset[: page_size + 1]
        self.page = list(queryset)

        if len(self.page) > page_size:
            self.has_next = True
            self.page = self.page[:page_size]
        else:
            self.has_next = False

        if cursor:
            self.has_previous = True
        else:
            self.has_previous = False

        return self.page

    def apply_cursor(self, queryset: Sequence[T], cursor: str) -> Sequence[T]:
        raise NotImplementedError("Subclasses must implement apply_cursor")

    def get_next_cursor(self) -> str | None:
        if not self.has_next or not self.page:
            return None
        last_item = self.page[-1]
        return self.encode_cursor(last_item)

    def get_previous_cursor(self) -> str | None:
        if not self.has_previous or not self.page:
            return None
        first_item = self.page[0]
        return self.encode_cursor(first_item)

    def encode_cursor(self, item: T) -> str:
        raise NotImplementedError("Subclasses must implement encode_cursor")

    def get_paginated_response(self, data: list[Any]) -> Response:
        return Response(
            {
                "results": data,
                "next_cursor": self.get_next_cursor(),
                "previous_cursor": self.get_previous_cursor(),
                "has_next": self.has_next,
                "has_previous": self.has_previous,
            }
        )

    def get_page_size(self, request: Request) -> int | None:
        if self.page_size_query_param:
            try:
                page_size = int(request.query_params[self.page_size_query_param])
                if page_size > 0:
                    return min(page_size, self.max_page_size)
            except KeyError, ValueError:
                pass
        return self.page_size


class OffsetPagination(BasePagination, Generic[T]):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    offset_query_param = "offset"

    def paginate_queryset(
        self, queryset: Sequence[T], request: Request, view=None
    ) -> list[T] | None:
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        offset = self.get_offset(request)
        self.count = len(queryset)
        self.page = list(queryset[offset : offset + page_size])
        return self.page

    def get_offset(self, request: Request) -> int:
        try:
            return int(request.query_params[self.offset_query_param])
        except KeyError, ValueError:
            return 0

    def get_page_size(self, request: Request) -> int | None:
        if self.page_size_query_param:
            try:
                page_size = int(request.query_params[self.page_size_query_param])
                if page_size > 0:
                    return min(page_size, self.max_page_size)
            except KeyError, ValueError:
                pass
        return self.page_size

    def get_paginated_response(self, data: list[Any]) -> Response:
        return Response(
            {
                "results": data,
                "count": self.count,
                "offset": self.get_offset(self.request) if hasattr(self, "request") else 0,
                "page_size": len(data),
            }
        )
