"""
API and External Services Configuration
"""
from typing import Optional
from pydantic import BaseModel, Field, SecretStr

class APIConfig(BaseModel):
    """API and external services configuration"""
    
    # OpenRouter Settings
    OPENROUTER_API_KEY: SecretStr = Field(
        "",
        description="OpenRouter API key"
    )
    OPENROUTER_TIMEOUT: int = Field(
        30, ge=1,
        description="OpenRouter API timeout in seconds" 
    )
    OPENROUTER_ENDPOINT: Optional[str] = Field(
        None,
        description="Custom OpenRouter endpoint URL"
    )

    # HDFS Settings
    HDFS_HOST: str = Field(
        "172.19.67.26",
        description="HDFS namenode host"
    )
    HDFS_PORT: int = Field(
        9000, ge=1, le=65535,
        description="HDFS namenode port"
    )
    HDFS_USER: str = Field(
        "hdfs",
        description="HDFS user"
    )
    HDFS_ROOT_DIR: str = Field(
        "/clickstream",
        description="HDFS root directory for application"
    )
    
    # Kafka Settings  
    KAFKA_BROKERS: Optional[str] = Field(
        None,
        description="Kafka brokers list (host:port)"
    )
    KAFKA_TOPIC: str = Field(
        "clickstream.events",
        description="Kafka topic for events"
    )
    KAFKA_BATCH_SIZE: int = Field(
        100, ge=1,
        description="Kafka producer batch size"
    )
    KAFKA_LINGER_MS: int = Field(
        100, ge=1,
        description="Kafka producer linger time (ms)"
    )
    KAFKA_COMPRESSION: str = Field(
        "snappy",
        description="Kafka compression type"
    )

    def get_hdfs_url(self) -> str:
        """Get complete HDFS URL"""
        return f"hdfs://{self.HDFS_HOST}:{self.HDFS_PORT}"

    class Config:
        env_prefix = "API_"