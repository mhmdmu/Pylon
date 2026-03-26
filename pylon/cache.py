import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

_ONE_YEAR_IN_SECONDS = 31536000


@dataclass
class CacheConfig:
    max_age: int = 60
    no_cache: bool = False
    no_store: bool = False
    private: bool = False
    public: bool = False
    immutable: bool = False

    def __post_init__(self):
        if self.public and self.private:
            raise ValueError(
                "public and private are mutually exclusive. Cannot set both"
            )

        if self.max_age < 0:
            raise ValueError("max_age must be non-negative")

        if self.immutable and self.max_age < _ONE_YEAR_IN_SECONDS:
            log.warning(
                "immutable is set with a small max_age (%s). Consider max_age=31536000.",
                self.max_age,
            )

    def build_cache_header(self) -> str:
        if self.no_store:
            return "no-store"  # nothing else matters

        header = []

        if self.no_cache:
            header.append("no-cache")  # skip max_age, meaningless
        else:
            header.append(f"max-age={self.max_age}")

        if self.private:
            header.append("private")
        elif self.public:
            header.append("public")

        if self.immutable:
            header.append("immutable")

        return ", ".join(header)
