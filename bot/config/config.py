from typing import Union

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    MIN_AVAILABLE_ENERGY: int = 100
    SLEEP_BY_MIN_ENERGY: Union[list[int], int] = [1800, 3600]

    ADD_TAPS_ON_TURBO: int = 2500

    AUTO_UPGRADE_TAP: bool = True
    MAX_TAP_LEVEL: int = 5
    AUTO_UPGRADE_ENERGY: bool = True
    MAX_ENERGY_LEVEL: int = 5
    AUTO_UPGRADE_CHARGE: bool = True
    MAX_CHARGE_LEVEL: int = 3

    APPLY_DAILY_ENERGY: bool = True
    APPLY_DAILY_TURBO: bool = True

    RANDOM_TAPS_COUNT: list[int] = [15, 75]
    SLEEP_BETWEEN_TAP: list[int] = [15, 25]

    USE_PROXY_FROM_FILE: bool = False

    USE_TAP_BOT: bool = False
    EMERGENCY_STOP: bool = False


settings = Settings()
