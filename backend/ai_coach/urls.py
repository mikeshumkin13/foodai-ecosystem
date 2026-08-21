from __future__ import annotations

from django.urls import path

from ai_coach.views import AICoachAskView, AICoachSettingsView

urlpatterns = [
    path("ai/coach/settings/", AICoachSettingsView.as_view(), name="ai-coach-settings"),
    path("ai/coach/ask/", AICoachAskView.as_view(), name="ai-coach-ask"),
]
