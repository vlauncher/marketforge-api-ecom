"""Reviews module package."""

from app.modules.reviews.models import Review, Rating
from app.modules.reviews.service import ReviewsService
from app.modules.reviews.router import router as reviews_router

__all__ = [
    "Review",
    "Rating",
    "ReviewsService",
    "reviews_router",
]