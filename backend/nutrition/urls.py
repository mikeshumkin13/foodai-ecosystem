from __future__ import annotations

from rest_framework.routers import SimpleRouter

from nutrition.views import FoodItemViewSet

router = SimpleRouter()
router.register("foods", FoodItemViewSet, basename="food")

urlpatterns = router.urls
