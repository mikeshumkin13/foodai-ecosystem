from __future__ import annotations

from django.urls import path

from wellbeing.views import WellbeingAskView, WellbeingAssistantSettingsView

urlpatterns = [
    path(
        "wellbeing/settings/",
        WellbeingAssistantSettingsView.as_view(),
        name="wellbeing-settings",
    ),
    path("wellbeing/ask/", WellbeingAskView.as_view(), name="wellbeing-ask"),
]
