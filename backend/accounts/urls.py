from __future__ import annotations

from rest_framework.routers import SimpleRouter

from accounts.views import (
    NutritionProfileViewSet,
    NutritionSensitiveRestrictionViewSet,
    UserProfileViewSet,
)

router = SimpleRouter()
router.register("profiles", UserProfileViewSet, basename="account-profile")
router.register(
    "nutrition-profiles",
    NutritionProfileViewSet,
    basename="account-nutrition-profile",
)
router.register(
    "nutrition-restrictions",
    NutritionSensitiveRestrictionViewSet,
    basename="account-nutrition-restriction",
)

urlpatterns = router.urls
