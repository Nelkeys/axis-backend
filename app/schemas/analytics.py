from pydantic import BaseModel

class AdminAnalyticsResponse(BaseModel):
    # Student & Viral Metrics
    total_students: int
    referred_students: int
    referral_share_percent: float

    # Engagement & Product Metrics
    total_enrollments: int
    completed_enrollments: int
    completion_rate_percent: float

    multi_course_students: int
    attach_rate_percent: float

    # Distribution & Unit Economics
    active_partners: int
    total_partner_commissions_naira: int
    users_acquired_by_partners: int
    partner_cac_naira: float