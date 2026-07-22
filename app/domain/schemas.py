"""Schemas returned by the domain API."""

from typing import Literal

from pydantic import BaseModel


class DomainStatusResponse(BaseModel):
    status: Literal["ready"]
    application: str
    version: str