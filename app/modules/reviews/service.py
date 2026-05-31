from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.modules.reviews.models import Review, Rating


class ReviewsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_review(
        self,
        product_id: int,
        user_id: int,
        rating: int,
        title: Optional[str],
        comment: Optional[str],
    ) -> Review:
        existing = await self.db.execute(
            select(Review).where(
                and_(
                    Review.product_id == product_id,
                    Review.user_id == user_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationError("You have already reviewed this product")

        review = Review(
            product_id=product_id,
            user_id=user_id,
            rating=rating,
            title=title,
            comment=comment,
            is_approved=False,
        )
        self.db.add(review)
        await self.db.flush()
        await self._update_product_rating(product_id)
        await self.db.refresh(review)
        return review

    async def get_review_by_id(self, review_id: int) -> Review:
        result = await self.db.execute(
            select(Review).where(Review.id == review_id)
        )
        review = result.scalar_one_or_none()
        if not review:
            raise NotFoundError("Review", str(review_id))
        return review

    async def list_product_reviews(
        self,
        product_id: int,
        approved_only: bool = True,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Review], int, float]:
        conditions = [Review.product_id == product_id]
        if approved_only:
            conditions.append(Review.is_approved == True)

        count_result = await self.db.execute(
            select(func.count()).select_from(Review).where(and_(*conditions))
        )
        total = count_result.scalar() or 0

        avg_result = await self.db.execute(
            select(func.avg(Review.rating)).where(and_(*conditions))
        )
        avg_rating = avg_result.scalar() or 0.0

        result = await self.db.execute(
            select(Review)
            .where(and_(*conditions))
            .order_by(Review.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        reviews = list(result.scalars().all())

        return reviews, total, round(avg_rating, 2) if avg_rating else 0.0

    async def update_review(
        self,
        review_id: int,
        user_id: int,
        rating: Optional[int],
        title: Optional[str],
        comment: Optional[str],
    ) -> Review:
        review = await self.get_review_by_id(review_id)
        if review.user_id != user_id:
            raise ValidationError("You can only update your own reviews")

        if rating is not None:
            review.rating = rating
        if title is not None:
            review.title = title
        if comment is not None:
            review.comment = comment

        review.is_approved = False
        await self.db.flush()
        await self._update_product_rating(review.product_id)
        await self.db.refresh(review)
        return review

    async def approve_review(self, review_id: int) -> Review:
        review = await self.get_review_by_id(review_id)
        review.is_approved = True
        await self.db.flush()
        await self.db.refresh(review)
        return review

    async def delete_review(self, review_id: int, user_id: int, is_admin: bool) -> None:
        review = await self.get_review_by_id(review_id)
        if review.user_id != user_id and not is_admin:
            raise ValidationError("You can only delete your own reviews")

        product_id = review.product_id
        await self.db.delete(review)
        await self.db.flush()
        await self._update_product_rating(product_id)

    async def _update_product_rating(self, product_id: int) -> None:
        result = await self.db.execute(
            select(
                func.avg(Review.rating),
                func.count(Review.id),
            ).where(
                and_(
                    Review.product_id == product_id,
                    Review.is_approved == True,
                )
            )
        )
        avg_rating, total = result.one()

        rating_result = await self.db.execute(
            select(Rating).where(Rating.product_id == product_id)
        )
        rating = rating_result.scalar_one_or_none()

        if rating:
            rating.average_rating = round(avg_rating, 2) if avg_rating else 0.0
            rating.total_reviews = total or 0
        else:
            rating = Rating(
                product_id=product_id,
                average_rating=round(avg_rating, 2) if avg_rating else 0.0,
                total_reviews=total or 0,
            )
            self.db.add(rating)

        await self.db.flush()

    async def get_product_rating(self, product_id: int) -> Optional[Rating]:
        result = await self.db.execute(
            select(Rating).where(Rating.product_id == product_id)
        )
        return result.scalar_one_or_none()