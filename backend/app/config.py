from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EHR Media Intelligence Platform"
    app_env: str = "development"
    database_path: str = "./storage/ehr.db"
    upload_dir: str = "./data/raw"
    fhir_bundle_dir: str = "./data/bundles"

    # Gemini API configuration
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    chroma_path: str = "./storage/chroma"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    max_upload_mb: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
