from dataclasses import dataclass, field


@dataclass
class CorsConfig:
    """CORS policy configuration"""

    allow_origins: str | list
    allow_methods: list = field(
        default_factory=lambda: ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
    )
    allow_headers: list = field(
        default_factory=lambda: ["Content-Type", "Authorization"]
    )
    allow_credentials: bool = False
    max_age: int = 3600

    def __post_init__(self):
        if self.allow_origins == "*" and self.allow_credentials:
            raise ValueError(
                "allow_credentials=True cannot be used with allow_origins='*'. Specify explicit origins instead."
            )

        if self.max_age < 0:
            raise ValueError("max_age must be non-negative")

        # Normalize origins; cleaner checks
        if not isinstance(self.allow_origins, list):
            self.allow_origins = [self.allow_origins]
