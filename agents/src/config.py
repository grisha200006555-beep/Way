from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    claude_model: str = "claude-haiku-4-5-20251001"
    claude_model_heavy: str = "claude-sonnet-4-6"

    telegram_bot_token: str = ""
    telegram_owner_id: int | None = None

    github_token: str = ""
    google_credentials_json: str = ""

    web_host: str = "0.0.0.0"
    web_port: int = 8000
    web_token: str = "change-me"

    database_url: str = "sqlite:///./agents.db"

    max_agent_iterations: int = 15
    sam_shell_whitelist: str = "ls,df,free,uptime,docker,systemctl,journalctl,uname,ps,cat,grep,tail,head"

    @property
    def shell_allowed(self) -> set[str]:
        return {c.strip() for c in self.sam_shell_whitelist.split(",") if c.strip()}


settings = Settings()
