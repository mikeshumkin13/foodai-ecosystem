from __future__ import annotations

from rest_framework.routers import SimpleRouter

from accounts.views import UserProfileViewSet

router = SimpleRouter()
router.register("profiles", UserProfileViewSet, basename="account-profile")

urlpatterns = router.urls
