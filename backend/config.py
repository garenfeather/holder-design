from __future__ import annotations

import os
from typing import Dict

# Centralized configuration for backend behaviour.
_CONFIG_MAP: Dict[str, Dict[str, str]] = {
    "dev": {
        "DOMAIN": "localhost",
        "API_BASE_URL": "http://localhost:8012",
    },
    "prod": {
        "DOMAIN": "182.254.192.55",
        "API_BASE_URL": "http://182.254.192.55:8012",
    },
}


def get_config() -> Dict[str, str]:
    """Return configuration based on HOLDER_ENV (default dev)."""
    env = os.environ.get("HOLDER_ENV", "dev").lower()
    if env not in _CONFIG_MAP:
        env = "dev"
    config = _CONFIG_MAP[env].copy()
    config["ENV"] = env
    return config


CONFIG = get_config()
