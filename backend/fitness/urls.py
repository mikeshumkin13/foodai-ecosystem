from __future__ import annotations

from rest_framework.routers import SimpleRouter

from fitness.views import ExerciseViewSet, WorkoutLogViewSet, WorkoutPlanViewSet

router = SimpleRouter()
router.register("fitness/exercises", ExerciseViewSet, basename="fitness-exercise")
router.register("fitness/plans", WorkoutPlanViewSet, basename="fitness-plan")
router.register("fitness/workout-logs", WorkoutLogViewSet, basename="fitness-workout-log")

urlpatterns = router.urls
