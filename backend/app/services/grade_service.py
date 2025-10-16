from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.db import models


class InstagramGradeService:
    """관리자 정의 등급 구간을 기반으로 인스타그램 등급을 계산."""

    DEFAULT_THRESHOLDS = [
        ("레드", 1000, 5000),
        ("블루", 5001, 30000),
        ("골드", 30001, 100000),
        ("프리미엄", 100001, None),
    ]

    def ensure_default_thresholds(self, db: Session) -> None:
        """기본 등급 구간이 없으면 삽입."""
        existing = {
            threshold.grade_name
            for threshold in db.query(models.InstagramGradeThreshold).all()
        }
        created = False
        for grade_name, min_view, max_view in self.DEFAULT_THRESHOLDS:
            if grade_name not in existing:
                db.add(
                    models.InstagramGradeThreshold(
                        grade_name=grade_name,
                        min_view_count=min_view,
                        max_view_count=max_view,
                    )
                )
                created = True
        if created:
            db.commit()

    def get_thresholds(self, db: Session) -> List[models.InstagramGradeThreshold]:
        """등급 구간을 최소 조회수 기준으로 정렬하여 반환."""
        return (
            db.query(models.InstagramGradeThreshold)
            .order_by(models.InstagramGradeThreshold.min_view_count.asc())
            .all()
        )

    def get_grade_for_average(self, db: Session, average_views: float) -> Optional[str]:
        """평균 조회수에 대해 등급을 반환."""
        thresholds = self.get_thresholds(db)
        for threshold in thresholds:
            if average_views < threshold.min_view_count:
                continue
            if threshold.max_view_count is not None and average_views > threshold.max_view_count:
                continue
            return threshold.grade_name
        return None


instagram_grade_service = InstagramGradeService()
