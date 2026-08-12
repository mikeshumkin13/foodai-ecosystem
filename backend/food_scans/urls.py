from __future__ import annotations

from rest_framework.routers import SimpleRouter

from food_scans.views import FoodScanViewSet

router = SimpleRouter()
router.register("food-scans", FoodScanViewSet, basename="food-scan")

urlpatterns = router.urls
