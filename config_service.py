import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware


DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}
KEYS = tuple(DEFAULTS)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def coerce(key: str, value):
    if key in {"port", "workers"}:
        return int(value)
    if key == "debug":
        return str(value).strip().lower() in {"true", "1", "yes", "on"}
    return str(value)


def load_config(cli_overrides: list[str]) -> dict:
    config = DEFAULTS.copy()

    env_name = os.getenv("APP_ENV", "development")
    yaml_path = Path(f"config.{env_name}.yaml")
    if yaml_path.exists():
        yaml_values = yaml.safe_load(yaml_path.read_text()) or {}
        for key, value in yaml_values.items():
            if key in KEYS:
                config[key] = coerce(key, value)

    file_values = dotenv_values(".env")
    for raw_key, value in file_values.items():
        if value is None:
            continue
        key = {"APP_PORT": "port", "APP_WORKERS": "workers", "NUM_WORKERS": "workers"}.get(raw_key)
        if key is None and raw_key.startswith("APP_"):
            key = raw_key[4:].lower()
        if key in KEYS:
            config[key] = coerce(key, value)

    for raw_key, value in os.environ.items():
        if not raw_key.startswith("APP_"):
            continue
        key = raw_key[4:].lower()
        if key in KEYS:
            config[key] = coerce(key, value)

    for assignment in cli_overrides:
        if "=" not in assignment:
            continue
        key, value = assignment.split("=", 1)
        key = key.strip().lower()
        if key in KEYS:
            config[key] = coerce(key, value.strip())

    config["api_key"] = "****"
    return config


@app.get("/effective-config")
async def effective_config(set: list[str] | None = Query(default=None)):
    return load_config(set or [])

