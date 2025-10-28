"""
Spark Configuration 
"""
from typing import Dict
from pydantic import BaseModel, Field
import os
import sys

class SparkConfig(BaseModel):
    """Apache Spark configuration settings"""

    # Core Settings
    MASTER: str = Field("local[*]", description="Spark master URL")
    MEMORY: str = Field("6g", description="Spark executor memory")
    EXECUTOR_CORES: int = Field(2, ge=1, description="Cores per executor")
    EXECUTOR_INSTANCES: int = Field(2, ge=1, description="Number of executors")
    
    # Environment
    JAVA_HOME: str = Field(
        os.environ.get("JAVA_HOME", r"C:\LUUDULIEU\APP\JDK\jdk-17.0.12"),
        description="Java home directory"
    )
    LOCAL_IP: str = Field(
        os.environ.get("SPARK_LOCAL_IP", "127.0.0.1"),
        description="Spark local IP"
    )
    PYTHON_PATH: str = Field(
        sys.executable,
        description="Python executable path"
    )

    # Advanced Configuration
    CONFIG: Dict[str, str] = Field(
        default={
            "spark.sql.adaptive.enabled": "true",
            "spark.sql.adaptive.coalescePartitions.enabled": "true", 
            "spark.sql.shuffle.partitions": "200",
            "spark.default.parallelism": "200",
            "spark.streaming.backpressure.enabled": "true",
            "spark.sql.warehouse.dir": "spark-warehouse",
            "spark.sql.session.timeZone": "UTC"
        },
        description="Additional Spark configuration"
    )

    def get_config(self) -> Dict[str, str]:
        """Get complete Spark configuration"""
        config = {
            "spark.master": self.MASTER,
            "spark.executor.memory": self.MEMORY,
            "spark.executor.cores": str(self.EXECUTOR_CORES),
            "spark.executor.instances": str(self.EXECUTOR_INSTANCES)
        }
        # Update environment
        os.environ["JAVA_HOME"] = self.JAVA_HOME
        os.environ["SPARK_LOCAL_IP"] = self.LOCAL_IP
        os.environ["PYSPARK_PYTHON"] = self.PYTHON_PATH
        os.environ["PYSPARK_DRIVER_PYTHON"] = self.PYTHON_PATH
        
        return {**config, **self.CONFIG}

    class Config:
        env_prefix = "SPARK_"