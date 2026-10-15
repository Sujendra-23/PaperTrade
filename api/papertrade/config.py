from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql://papertrade:papertrade@localhost:55432/papertrade"
    redis_url: str = "redis://localhost:56379/0"
    engine_address: str = "localhost:50051"
    simulator_enabled: bool = True
    secure_cookies: bool = False
    max_order_size: int = 1000
    max_position: int = 2000


settings = Settings()
