from __future__ import annotations

from django.urls import path
from rest_framework.routers import SimpleRouter

from diary.views import DiaryDayView, MealViewSet

router = SimpleRouter()
router.register("meals", MealViewSet, basename="meal")

urlpatterns = [
    *router.urls,
    path("diary/day/", DiaryDayView.as_view(), name="diary-day"),
]
