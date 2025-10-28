"""
API Response Models
Centralized model definitions for the API endpoints.
Follows a hierarchical structure:
1. Basic shared models
2. Component-specific models
3. Composite analysis models
4. Comprehensive analysis model
"""
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator
from bson import ObjectId

# Base Response Models
class ErrorResponse(BaseModel):
    """Standard error response"""
    message: str
    detail: Optional[Dict[str, Any]] = None

class Token(BaseModel):
    """Authentication token response"""
    access_token: str
    token_type: str = Field(default="bearer", pattern="^bearer$")
    expires_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

# Basic Metric Models
class TimeMetrics(BaseModel):
    """Time-based metrics shared across analyses"""
    start_time: datetime
    end_time: datetime
    duration: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Basic E-commerce Models
class BusinessMetrics(BaseModel):
    """Core business performance metrics"""
    revenue: float
    orders: int
    average_order_value: float
    conversion_rate: float
    customer_acquisition_cost: Optional[float] = None
    customer_lifetime_value: Optional[float] = None
    roi: Optional[float] = None

class UserBehaviorMetrics(BaseModel):
    """Aggregate user behavior metrics"""
    active_users: int
    new_users: int
    returning_users: int
    sessions_per_user: float
    avg_session_duration: float
    bounce_rate: float
    engagement_score: float

class BehaviorPattern(BaseModel):
    """Pattern in user behavior"""
    pattern_type: str  # e.g., "navigation", "interaction", "conversion"
    frequency: int
    user_count: int
    conversion_rate: Optional[float] = None
    avg_duration: Optional[float] = None
    associated_events: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class UserAction(BaseModel):
    """Individual user action/event"""
    action_type: str
    timestamp: datetime
    page: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    duration: Optional[float] = None
    success: Optional[bool] = None

class BehaviorSegment(BaseModel):
    """Behavioral user segment"""
    segment_name: str
    user_count: int
    dominant_patterns: List[str]
    engagement_level: float
    conversion_rate: float
    avg_session_frequency: float
    key_characteristics: List[str]

class BehaviorAnalysis(BaseModel):
    """Complete user behavior analysis"""
    metrics: UserBehaviorMetrics
    common_patterns: List[BehaviorPattern]
    user_actions: List[UserAction]
    segments: List[BehaviorSegment]
    anomalies: List[Dict[str, Any]]
    opportunities: List[Dict[str, Any]]
    recommendations: List[str]

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

# Recommendation Models
class ProductRecommendation(BaseModel):
    """Individual product recommendation"""
    product_id: str
    product_name: str
    category: str
    confidence_score: float
    relevance_score: float
    price: Optional[float] = None
    reason: str
    features_matched: List[str] = Field(default_factory=list)
    similar_products: List[str] = Field(default_factory=list)

class CategoryRecommendation(BaseModel):
    """Category-based recommendation"""
    category: str
    relevance_score: float
    recommended_products: List[ProductRecommendation]
    user_affinity: float
    historical_performance: Dict[str, float]

class PersonalizedRecommendation(BaseModel):
    """User-specific recommendations"""
    user_id: str
    affinity_scores: Dict[str, float]
    preferred_categories: List[str]
    recommendations: List[ProductRecommendation]
    context: Dict[str, Any] = Field(default_factory=dict)

class Recommendations(BaseModel):
    """Complete recommendations response"""
    personalized: List[PersonalizedRecommendation]
    category_based: List[CategoryRecommendation]
    trending_products: List[ProductRecommendation]
    similar_products: List[ProductRecommendation]
    seasonal_recommendations: List[ProductRecommendation]
    cross_sell_suggestions: List[Dict[str, List[ProductRecommendation]]]
    recommendation_metrics: Dict[str, float]
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

# Business Insights Models
class MetricInsight(BaseModel):
    """Individual metric insight"""
    metric_name: str
    current_value: float
    previous_value: Optional[float] = None
    change_percentage: Optional[float] = None
    trend_direction: str  # "up", "down", "stable"
    significance: float  # 0-1 score of insight importance
    context: str
    recommendations: List[str] = Field(default_factory=list)

class TrendInsight(BaseModel):
    """Trend-based insight"""
    trend_type: str  # e.g., "seasonal", "growth", "decline"
    metrics_affected: List[str]
    start_date: datetime
    end_date: datetime
    magnitude: float
    confidence: float
    description: str
    supporting_data: Dict[str, Any] = Field(default_factory=dict)

class AnomalyInsight(BaseModel):
    """Anomaly detection insight"""
    anomaly_type: str
    detected_at: datetime
    affected_metrics: List[str]
    severity: float  # 0-1 score
    normal_range: Dict[str, float]
    actual_value: float
    possible_causes: List[str]
    recommended_actions: List[str]

class CorrelationInsight(BaseModel):
    """Correlation between metrics"""
    metrics_involved: List[str]
    correlation_coefficient: float
    confidence: float
    causation_likelihood: Optional[float] = None
    description: str
    business_impact: str
    action_items: List[str]

class OpportunityInsight(BaseModel):
    """Business opportunity insight"""
    opportunity_type: str
    potential_impact: Dict[str, float]
    effort_required: str  # "low", "medium", "high"
    priority_score: float
    target_segments: List[str]
    implementation_steps: List[str]
    resources_needed: List[str]
    expected_roi: Optional[float] = None

class Insights(BaseModel):
    """Complete business insights response"""
    key_metrics: List[MetricInsight]
    trends: List[TrendInsight]
    anomalies: List[AnomalyInsight]
    correlations: List[CorrelationInsight]
    opportunities: List[OpportunityInsight]
    summary: str
    priority_actions: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

class TrendAnalysis(BaseModel):
    """Time-based trend analysis"""
    metric_name: str
    period_start: datetime
    period_end: datetime
    values: List[float]
    change_vs_previous: float
    trend_direction: str
    seasonality: Optional[bool] = None

# Journey Analysis Models 
class JourneyStep(BaseModel):
    """Individual step in user journey"""
    step_number: int
    page: str
    event_type: str
    timestamp: datetime
    duration: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class JourneyPath(BaseModel):
    """Complete path through the application"""
    path_id: str
    user_id: str
    session_id: str
    steps: List[JourneyStep]
    start_time: datetime
    end_time: Optional[datetime] = None
    conversion_achieved: bool = False
    revenue: Optional[float] = None

class JourneyMetrics(BaseModel):
    """Metrics for journey analysis"""
    total_journeys: int
    avg_journey_length: float
    avg_journey_duration: float
    conversion_rate: float
    popular_paths: List[Dict[str, Any]]
    drop_off_points: List[Dict[str, Any]]

class JourneyAnalysis(BaseModel):
    """Complete journey analysis response"""
    metrics: JourneyMetrics
    paths: List[JourneyPath]
    segments: List[Dict[str, Any]]
    conversion_paths: List[Dict[str, Any]]
    recommendations: List[str]

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

# Session Analysis Models
class SessionEvent(BaseModel):
    """Individual event in a session"""
    event_id: str
    event_type: str 
    timestamp: datetime
    page: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SessionMetrics(BaseModel):
    """Core session metrics"""
    total_sessions: int
    avg_session_duration: float
    bounce_rate: float
    pages_per_session: float
    conversion_rate: float

class UserSession(BaseModel):
    """Complete user session data"""
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    events: List[SessionEvent]
    duration: Optional[float]
    pages_viewed: int
    converted: bool = False
    
class SessionAnalysis(BaseModel):
    """Complete session analysis response"""
    metrics: SessionMetrics
    sessions: List[UserSession]
    event_flows: List[Dict[str, Any]]
    user_segments: List[Dict[str, Any]]
    recommendations: List[str]

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

# Cart Analysis Models
class CartItem(BaseModel):
    """Individual item in cart analysis"""
    product_id: str
    product_name: str
    quantity: int
    price: float
    category: str
    abandoned: bool = False
    time_in_cart: Optional[float] = None

class CartMetrics(BaseModel):
    """Cart-level metrics"""
    total_carts: int
    active_carts: int
    abandoned_carts: int
    abandonment_rate: float
    avg_items_per_cart: float
    avg_cart_value: float
    total_cart_value: float

class CartAbandonmentReason(BaseModel):
    """Analysis of cart abandonment reasons"""
    reason: str
    count: int
    percentage: float
    affected_products: List[str]

class CartAnalysis(BaseModel):
    """Complete cart analysis response"""
    metrics: CartMetrics
    items: List[CartItem]
    abandonment_reasons: List[CartAbandonmentReason]
    high_abandonment_categories: List[Dict[str, Any]]
    recommendations: List[str]
    recovery_opportunities: List[Dict[str, Any]]

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

# SEO Analysis Models
class PageMetrics(BaseModel):
    """SEO metrics for a specific page"""
    url: str
    title: Optional[str] = None
    views: int
    unique_visitors: int
    avg_time_on_page: float
    bounce_rate: float
    exit_rate: float
    conversion_rate: Optional[float] = None
    organic_traffic: Optional[int] = None

class SearchKeywordMetrics(BaseModel):
    """Analytics for search keywords"""
    keyword: str
    search_volume: int
    position: float
    clicks: int
    impressions: int
    ctr: float
    conversion_rate: Optional[float] = None

class ContentPerformance(BaseModel):
    """Content performance metrics"""
    content_type: str
    engagement_rate: float
    shares: int
    comments: int
    avg_time_engaged: float
    conversion_contribution: Optional[float] = None

class SEOAnalysis(BaseModel):
    """Complete SEO analysis response"""
    site_metrics: Dict[str, Any]  # Overall site metrics
    top_pages: List[PageMetrics]
    top_keywords: List[SearchKeywordMetrics]
    content_performance: List[ContentPerformance]
    technical_issues: List[Dict[str, Any]]
    opportunity_keywords: List[Dict[str, Any]]
    recommendations: List[str]
    competitive_gaps: List[Dict[str, Any]]

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

# Retention Analysis Models
class CohortMetrics(BaseModel):
    """Metrics for a specific user cohort"""
    cohort_size: int
    retention_rate: float
    churn_rate: float
    avg_session_frequency: float
    avg_order_value: Optional[float] = None
    lifetime_value: Optional[float] = None

class RetentionPeriod(BaseModel):
    """Retention data for a specific time period"""
    period: str  # e.g., "Week 1", "Month 1"
    active_users: int
    retention_rate: float
    new_users: int
    churned_users: int
    reactivated_users: Optional[int] = None

class UserSegment(BaseModel):
    """Analysis of a specific user segment"""
    segment_name: str
    user_count: int
    avg_retention_rate: float
    top_features: List[str]
    engagement_score: float
    churn_risk: Optional[float] = None

class RetentionAnalysis(BaseModel):
    """Complete user retention analysis"""
    overall_retention_rate: float
    cohort_metrics: List[CohortMetrics]
    retention_periods: List[RetentionPeriod]
    user_segments: List[UserSegment]
    churn_indicators: List[Dict[str, Any]]
    engagement_factors: List[Dict[str, Any]]
    recommendations: List[str]
    risk_alerts: List[str]

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
        
# Comprehensive Analytics Models
class OverallMetrics(BaseModel):
    """High level metrics across all analyses"""
    total_users: int
    total_sessions: int
    total_conversions: int
    total_revenue: float
    avg_order_value: float
    conversion_rate: float
    bounce_rate: float
    
class TrendMetrics(BaseModel):
    """Trend analysis over time"""
    period: str  # daily/weekly/monthly
    metrics: List[Dict[str, Any]]
    growth_rate: Dict[str, float]
    trending_products: List[Dict[str, Any]]
    trending_categories: List[Dict[str, Any]]

class UserSegmentMetrics(BaseModel):
    """Metrics broken down by user segment"""
    segment_name: str
    user_count: int
    conversion_rate: float
    avg_order_value: float
    lifetime_value: float
    retention_rate: float
    engagement_score: float

class ComprehensiveAnalysis(BaseModel):
    """Complete analytics overview combining all analyses"""
    overall_metrics: OverallMetrics
    trends: TrendMetrics
    segments: List[UserSegmentMetrics]
    journey_analysis: JourneyAnalysis
    session_analysis: SessionAnalysis 
    cart_analysis: CartAnalysis
    retention_analysis: RetentionAnalysis
    seo_analysis: SEOAnalysis
    recommendations: List[str]
    alerts: List[Dict[str, Any]]
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }

    @validator('duration', pre=True)
    def calculate_duration(cls, v, values):
        if 'start_time' in values and 'end_time' in values and values['end_time']:
            return (values['end_time'] - values['start_time']).total_seconds()
        return v

class PerformanceMetrics(BaseModel):
    """Performance metrics shared across analyses"""
    total_count: int
    success_count: int
    error_count: int
    success_rate: float

    @validator('success_rate', pre=True)
    def calculate_rate(cls, v, values):
        if 'total_count' in values and values['total_count'] > 0:
            return values['success_count'] / values['total_count']
        return 0.0

class CartItem(BaseModel):
    """Individual item in cart analysis"""
    product_id: str
    product_name: str
    quantity: int
    price: float
    category: str
    abandoned: bool = False
    time_in_cart: Optional[float] = None

class CartMetrics(BaseModel):
    """Cart-level metrics"""
    total_carts: int
    active_carts: int
    abandoned_carts: int
    abandonment_rate: float
    avg_items_per_cart: float
    avg_cart_value: float
    total_cart_value: float

class CartAbandonmentReason(BaseModel):
    """Analysis of cart abandonment reasons"""
    reason: str
    count: int
    percentage: float
    affected_products: List[str]

class CartAnalysis(BaseModel):
    """Complete cart analysis response"""
    metrics: CartMetrics
    items: List[CartItem]
    abandonment_reasons: List[CartAbandonmentReason]
    high_abandonment_categories: List[Dict[str, Any]]
    recommendations: List[str]
    recovery_opportunities: List[Dict[str, Any]]

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class CohortMetrics(BaseModel):
    """Metrics for a specific user cohort"""
    cohort_size: int
    retention_rate: float
    churn_rate: float
    avg_session_frequency: float
    avg_order_value: Optional[float] = None
    lifetime_value: Optional[float] = None

class RetentionPeriod(BaseModel):
    """Retention data for a specific time period"""
    period: str  # e.g., "Week 1", "Month 1"
    active_users: int
    retention_rate: float
    new_users: int
    churned_users: int
    reactivated_users: Optional[int] = None

class UserSegment(BaseModel):
    """Analysis of a specific user segment"""
    segment_name: str
    user_count: int
    avg_retention_rate: float
    top_features: List[str]
    engagement_score: float
    churn_risk: Optional[float] = None

class RetentionAnalysis(BaseModel):
    """Complete user retention analysis"""
    overall_retention_rate: float
    cohort_metrics: List[CohortMetrics]
    retention_periods: List[RetentionPeriod]
    user_segments: List[UserSegment]
    churn_indicators: List[Dict[str, Any]]
    engagement_factors: List[Dict[str, Any]]
    recommendations: List[str]
    risk_alerts: List[str]

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class PageMetrics(BaseModel):
    """SEO metrics for a specific page"""
    url: str
    title: Optional[str] = None
    views: int
    unique_visitors: int
    avg_time_on_page: float
    bounce_rate: float
    exit_rate: float
    conversion_rate: Optional[float] = None
    organic_traffic: Optional[int] = None

class SearchKeywordMetrics(BaseModel):
    """Analytics for search keywords"""
    keyword: str
    search_volume: int
    click_through_rate: float
    conversion_rate: Optional[float] = None
    bounce_rate: float
    avg_position: Optional[float] = None
    related_pages: List[str]

class ContentPerformance(BaseModel):
    """Content performance metrics"""
    url: str
    content_type: str
    engagement_score: float
    sharing_metrics: Dict[str, int]
    readability_score: Optional[float] = None
    avg_scroll_depth: Optional[float] = None
    content_gaps: List[str]

class SEOAnalysis(BaseModel):
    """Complete SEO analysis response"""
    site_metrics: Dict[str, Any]  # Overall site metrics
    top_pages: List[PageMetrics]
    top_keywords: List[SearchKeywordMetrics]
    content_performance: List[ContentPerformance]
    technical_issues: List[Dict[str, Any]]
    opportunity_keywords: List[Dict[str, Any]]
    recommendations: List[str]
    competitive_gaps: List[Dict[str, Any]]

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class BusinessMetrics(BaseModel):
    """Core business performance metrics"""
    revenue: float
    orders: int
    average_order_value: float
    conversion_rate: float
    customer_acquisition_cost: Optional[float] = None
    customer_lifetime_value: Optional[float] = None
    roi: Optional[float] = None

class UserBehaviorMetrics(BaseModel):
    """Aggregate user behavior metrics"""
    total_users: int
    active_users: int
    new_users: int
    returning_users: int
    engagement_rate: float
    avg_session_duration: float
    pages_per_session: float

class TrendAnalysis(BaseModel):
    """Time-based trend analysis"""
    period: str
    metrics: Dict[str, float]
    growth_rate: Dict[str, float]
    seasonality: Optional[Dict[str, Any]] = None
    anomalies: List[Dict[str, Any]]

class ComprehensiveAnalysis(BaseModel):
    """Complete e-commerce analytics response combining all analyses"""
    # Overall Business Health
    business_metrics: BusinessMetrics
    user_behavior: UserBehaviorMetrics
    trends: List[TrendAnalysis]
    
    # Detailed Analytics
    journey_analysis: JourneyAnalysis
    cart_analysis: CartAnalysis
    retention_analysis: RetentionAnalysis
    seo_analysis: SEOAnalysis
    
    # Insights and Actions
    key_insights: List[str]
    alerts: List[Dict[str, Any]]
    opportunities: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    
    # AI-Generated Analysis
    predictive_metrics: Dict[str, Any]
    customer_segments: List[Dict[str, Any]]
    product_insights: List[Dict[str, Any]]
    
    # Metadata
    analysis_timestamp: datetime
    data_freshness: Dict[str, datetime]
    analysis_period: Dict[str, datetime]

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class SessionMetrics(BaseModel):
    """Session-level analytics metrics"""
    total_sessions: int
    avg_session_duration: float
    bounce_rate: float
    pages_per_session: float
    conversion_rate: Optional[float] = None

class PathSegment(BaseModel):
    """Single segment in a user journey path"""
    page: str
    event_type: str
    duration: Optional[float] = None
    conversion_rate: Optional[float] = None
    drop_off_rate: Optional[float] = None

class JourneyPath(BaseModel):
    """Complete user journey path with analytics"""
    path_id: str
    segments: List[PathSegment]
    frequency: int
    conversion_rate: float
    avg_duration: float
    start_page: str
    end_page: str

class FunnelStep(BaseModel):
    """Single step in conversion funnel"""
    name: str
    count: int
    rate: float
    drop_off: Optional[float] = None

class JourneyAnalysis(BaseModel):
    """Complete user journey analysis response"""
    session_metrics: SessionMetrics
    top_paths: List[JourneyPath]
    conversion_funnel: List[FunnelStep]
    time_to_convert: Optional[float] = None
    popular_entry_points: List[Dict[str, Any]]
    popular_exit_points: List[Dict[str, Any]]
    recommendations: List[str]
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class ErrorResponse(BaseModel):
    """Standard error response"""
    message: str
    error_code: Optional[str] = None
    
class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "ok"
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    
class UserResponse(BaseModel):
    """User response"""
    id: str
    username: str
    email: str
    created_at: datetime
    is_active: bool
    roles: List[str] = []
    
class ProductResponse(BaseModel):
    """Product response"""
    id: str
    name: str
    description: Optional[str]
    price: float
    category: str
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime
    
class EventResponse(BaseModel):
    """Event response"""
    id: str
    type: str
    user_id: str
    session_id: str
    timestamp: datetime
    properties: Dict[str, Any] = {}
    
class AnalysisResponse(BaseModel):
    """Analysis response"""
    id: str
    user_id: str
    type: str
    parameters: Dict[str, Any] = {}
    results: Dict[str, Any] = {}
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    error: Optional[str]
    
class RecommendationResponse(BaseModel):
    """Recommendation response"""
    user_id: str
    recommendations: List[Dict[str, Any]]
    score: float
    generated_at: datetime
    model_version: str
    
class MetricsResponse(BaseModel):
    """Metrics response"""
    timeframe: str  
    metrics: Dict[str, Any]
    dimensions: Dict[str, Any] = {}
    aggregations: Dict[str, Any] = {}