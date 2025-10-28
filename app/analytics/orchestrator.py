"""
Analytics Orchestrator
Coordinates execution of analytics modules
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional, Any

from .base import AnalyticsModule, AnalyticsResult

logger = logging.getLogger(__name__)

class AnalyticsOrchestrator:
    """
    Orchestrates execution of analytics modules
    
    Manages parallel and sequential execution of modules,
    handles errors, and aggregates results.
    """
    
    def __init__(self, modules: Optional[List[AnalyticsModule]] = None):
        self.modules = modules or []
        self.results: Dict[str, AnalyticsResult] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
    def add_module(self, module: AnalyticsModule):
        """Add analytics module"""
        self.modules.append(module)
        
    def run_module(self, module: AnalyticsModule, username: Optional[str], limit: Optional[int]):
        """
        Execute single module with error handling
        
        Args:
            module: Analytics module to run
            username: Optional username filter
            limit: Optional event limit
        """
        logger.info(f"Running module: {module.name}")
        
        try:
            result = module.execute(username, limit)
            self.results[module.name] = result
            
            if result.error:
                logger.error(f"Module {module.name} failed: {result.error}")
            else:
                logger.info(
                    f"Module {module.name} completed in {result.duration:.2f}s"
                )
                
        except Exception as e:
            logger.exception(f"Error in module {module.name}")
            self.results[module.name] = AnalyticsResult(
                module_name=module.name,
                start_time=datetime.now(),
                error=str(e)
            )
    
    def run_all(self, username: Optional[str] = None, limit: Optional[int] = None, 
                max_workers: int = 4) -> Dict[str, Any]:
        """
        Run all registered modules
        
        Args:
            username: Optional username filter
            limit: Optional event limit  
            max_workers: Max parallel workers
            
        Returns:
            Dict with execution results and stats
        """
        self.start_time = datetime.now()
        logger.info(
            f"Starting analytics run - User: {username or 'ALL'}, "
            f"Limit: {limit or 'None'}, Workers: {max_workers}"
        )
        
        # Split modules by execution mode
        parallel = []
        sequential = []
        for module in self.modules:
            (parallel if module.parallel else sequential).append(module)
            
        # Run sequential modules
        for module in sequential:
            self.run_module(module, username, limit)
            
        # Run parallel modules
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.run_module, module, username, limit): module
                for module in parallel
            }
            for future in as_completed(futures):
                module = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.exception(f"Error in module {module.name}")
                    
        # Complete execution
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        # Calculate stats
        total = len(self.modules)
        successful = sum(1 for r in self.results.values() if not r.error)
        failed = total - successful
        
        return {
            "status": "completed",
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": duration,
            "statistics": {
                "total_modules": total,
                "successful": successful,
                "failed": failed,
                "parallel_modules": len(parallel),
                "sequential_modules": len(sequential)
            },
            "results": {
                name: result.dict() 
                for name, result in self.results.items()
            }
        }