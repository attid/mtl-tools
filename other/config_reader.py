import os

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

start_path = os.path.dirname(os.path.dirname(__file__)) + '/'
dotenv_path = os.path.join(start_path, '.env')

class Settings(BaseSettings):
    bot_token: SecretStr
    test_token: SecretStr
    base_fee: int
    redis_url: str
    #firebird_url: str
    postgres_url: str
    openai_key: SecretStr
    openrouter_key: SecretStr | None = None
    private_sign: SecretStr
    currencylayer_id: str
    coinlayer_id: str
    debank: SecretStr
    eurmtl_key: str
    sentry_dsn: str
    sentry_report_dsn: str
    horizon_url: str
    stellar_testnet: bool = False
    coinmarketcap: SecretStr
    #mongodb_url: str
    pyro_api_id: int = 0
    pyro_api_hash: SecretStr | None = None
    grist_token: str
    miniapps_key: str | None = None
    test_mode: bool = True

    # Stellar Notifier webhook settings
    notifier_url: str | None = None  # http://operations-notifier:8000
    webhook_public_url: str | None = None  # http://skynet_bot:8081/webhook
    webhook_port: int = 8081
    notifier_auth_token: str | None = None  # Bearer token for notifier API

    model_config = SettingsConfigDict(
        env_file=dotenv_path,
        env_file_encoding='utf-8',
        extra='allow',
        case_sensitive=False
    )


config: Settings = Settings()  # type: ignore[call-arg]

if os.getenv('ENVIRONMENT', 'test') == 'production':
    config.test_mode = False
else:
    config.test_mode = True
