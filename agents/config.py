"""
Base configuration and utilities for all agents
"""

import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional

load_dotenv()


@dataclass
class AgentConfig:
    """Configuration for AI agents"""
    
    # Database
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: str = os.getenv("DB_PORT", "5432")
    db_name: str = os.getenv("DB_NAME", "clinical_supply_chain")
    db_user: str = os.getenv("DB_USER", "postgres")
    db_password: str = os.getenv("DB_PASSWORD", "")
    
    # LLM
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    max_tokens: int = int(os.getenv("MAX_TOKENS", "4096"))
    
    # API Keys
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    # Risk thresholds
    expiry_critical_days: int = int(os.getenv("EXPIRY_CRITICAL_DAYS", "30"))
    expiry_high_days: int = int(os.getenv("EXPIRY_HIGH_DAYS", "60"))
    expiry_medium_days: int = int(os.getenv("EXPIRY_MEDIUM_DAYS", "90"))
    shortfall_horizon_weeks: int = int(os.getenv("SHORTFALL_HORIZON_WEEKS", "8"))
    
    # Monitoring
    enable_daily_monitoring: bool = os.getenv("ENABLE_DAILY_MONITORING", "true").lower() == "true"
    monitoring_schedule: str = os.getenv("MONITORING_SCHEDULE", "0 6 * * *")
    
    # Alerts
    alert_email_from: str = os.getenv("ALERT_EMAIL_FROM", "")
    alert_email_to: str = os.getenv("ALERT_EMAIL_TO", "")
    smtp_server: str = os.getenv("SMTP_SERVER", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "logs/agent.log")
    
    @property
    def db_connection_string(self) -> str:
        """Get PostgreSQL connection string"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    def validate(self) -> bool:
        """Validate configuration"""
        errors = []
        
        if not self.db_password:
            errors.append("DB_PASSWORD is not set")
        
        if not self.openai_api_key and not self.anthropic_api_key:
            errors.append("Either OPENAI_API_KEY or ANTHROPIC_API_KEY must be set")
        
        if errors:
            for error in errors:
                print(f"✗ Configuration Error: {error}")
            return False
        
        return True


# Global config instance
config = AgentConfig()
