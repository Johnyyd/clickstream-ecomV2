"""
Analytics Module Package
Provides unified interface for all analytics operations
"""

from .base import AnalyticsModule, AnalyticsResult
from .orchestrator import AnalyticsOrchestrator
from .modules import (
    SEOAnalytics,
    CartAnalytics,
    RetentionAnalytics, 
    JourneyAnalytics,
    RecommendationAnalytics,
    SegmentationAnalytics
)

__all__ = [
    'AnalyticsModule',
    'AnalyticsResult',
    'AnalyticsOrchestrator',
    'SEOAnalytics',
    'CartAnalytics', 
    'RetentionAnalytics',
    'JourneyAnalytics',
    'RecommendationAnalytics',
    'SegmentationAnalytics'
]