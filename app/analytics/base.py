"""
Base Analytics Classes
Defines core analytics functionality and interfaces
"""
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

class AnalyticsResult(BaseModel):
    """Standard analytics result structure"""
    
    module_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    results: Dict[str, Any] = {}

    def mark_complete(self):
        """Mark analysis as complete and calculate duration"""
        self.end_time = datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()

    def add_error(self, error: str):
        """Add error message"""
        self.error = str(error)
        self.mark_complete()

    class Config:
        arbitrary_types_allowed = True

class AnalyticsModule:
    """Base class for analytics modules"""
    
    def __init__(self, name: str, parallel: bool = True):
        self.name = name
        self.parallel = parallel
        self._last_result: Optional[AnalyticsResult] = None
    
    @property
    def last_result(self) -> Optional[AnalyticsResult]:
        """Get last execution result"""
        return self._last_result

    def execute(self, username: Optional[str] = None, limit: Optional[int] = None) -> AnalyticsResult:
        """
        Execute analytics module
        
        Args:
            username: Optional username to filter data
            limit: Optional limit on number of events
            
        Returns:
            AnalyticsResult with execution details
        """
        result = AnalyticsResult(
            module_name=self.name,
            start_time=datetime.now(),
            metadata={
                "username": username,
                "limit": limit,
                "parallel": self.parallel
            }
        )
        
        try:
            # Run actual analysis
            analysis_results = self.run_analysis(username, limit)
            result.results = analysis_results
            
        except Exception as e:
            result.add_error(str(e))
            raise
            
        finally:
            result.mark_complete()
            self._last_result = result
            
        return result

    def run_analysis(self, username: Optional[str], limit: Optional[int]) -> Dict[str, Any]:
        """
        Implement actual analysis logic in subclasses
        
        Args:
            username: Optional username to filter data
            limit: Optional limit on number of events
            
        Returns:
            Dict containing analysis results
        """
        raise NotImplementedError(
            f"Module {self.name} must implement run_analysis()"
        )