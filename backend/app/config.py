from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "股票因子挖掘工作台"
    version: str = "1.0.0"
    
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_enabled: bool = True
    
    cache_ttl: int = 3600
    
    data_dir: str = "./data"
    max_upload_size: int = 1073741824
    
    class Config:
        env_file = ".env"


settings = Settings()
