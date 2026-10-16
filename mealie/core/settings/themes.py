from pydantic_settings import BaseSettings, SettingsConfigDict


class Theme(BaseSettings):
    light_primary: str = "#2F6B4F"
    light_accent: str = "#4A6072"
    light_secondary: str = "#C98A1B"
    light_success: str = "#2F6B4F"
    light_info: str = "#4A6072"
    light_warning: str = "#D9822B"
    light_error: str = "#C2413A"

    dark_primary: str = "#7FBF9E"
    dark_accent: str = "#AFC2D0"
    dark_secondary: str = "#E8B44F"
    dark_success: str = "#7FBF9E"
    dark_info: str = "#AFC2D0"
    dark_warning: str = "#EFA35B"
    dark_error: str = "#E5776F"
    model_config = SettingsConfigDict(env_prefix="theme_", extra="allow")
