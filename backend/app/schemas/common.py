from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, StringConstraints


def _is_uuid(value: str) -> str:
    return str(UUID(value))


# A database id. Stays a str for services, but a malformed value is a 422, not a Postgres error
UuidStr = Annotated[str, AfterValidator(_is_uuid)]
ShortText = Annotated[str, StringConstraints(max_length=100)]

MAX_YEARS_EXPERIENCE = 80
MAX_CONSULTATION_FEE = 1_000_000
MAX_QUALIFICATIONS = 20
MAX_SPECIALTIES = 10
MAX_BIO_LENGTH = 2000
MAX_REASON_LENGTH = 500
