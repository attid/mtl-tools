import os

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

start_path = os.path.dirname(os.path.dirname(__file__)) + '/'
dotenv_path = os.path.join(start_path, '.env')

class Settings(BaseSettings):
    bot_token: SecretStr
    test_token: SecretStr
    base_fee: int
    db_dns: str
    openai_key: SecretStr
    private_sign: SecretStr
    currencylayer_id: str
    coinlayer_id: str
    debank: SecretStr
    eurmtl_key: str
    sentry_dsn: str
    sentry_report_dsn: str
    horizon_url: str
    coinmarketcap: SecretStr
    mongodb_url: str
    pyro_api_id: int
    pyro_api_hash: SecretStr
    telegraph_token: str
    grist_token: str

    model_config = SettingsConfigDict(
        env_file=dotenv_path,
        env_file_encoding='utf-8',
        extra='allow',
        case_sensitive=False
    )


config = Settings()
