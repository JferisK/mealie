from pydantic_settings import BaseSettings, SettingsConfigDict


class Theme(BaseSettings):
    light_primary: str = "#2F6B4F"
    light_accent: str = "#3F5E96"
    light_secondary: str = "#C98A1B"
    light_success: str = "#3C8D5A"
    light_info: str = "#3F5E96"
    light_warning: str = "#D9822B"
    light_error: str = "#C2413A"

    dark_primary: str = "#7FBF9E"
    dark_accent: str = "#9DB4E0"
    dark_secondary: str = "#E8B44F"
    dark_success: str = "#6DBB8A"
    dark_info: str = "#9DB4E0"
    dark_warning: str = "#EFA35B"
    dark_error: str = "#E5776F"
    model_config = SettingsConfigDict(env_prefix="theme_", extra="allow")
