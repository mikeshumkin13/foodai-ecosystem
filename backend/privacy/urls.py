from __future__ import annotations

from django.urls import path

from privacy.views import (
    PrivacyAccountDeleteView,
    PrivacyAIChatHistoryDeleteView,
    PrivacyConsentView,
    PrivacyDataExportView,
    PrivacyDataSummaryView,
    PrivacyFoodPhotoDeleteView,
)

urlpatterns = [
    path("privacy/data-summary/", PrivacyDataSummaryView.as_view(), name="privacy-data-summary"),
    path("privacy/export/", PrivacyDataExportView.as_view(), name="privacy-data-export"),
    path("privacy/consent/", PrivacyConsentView.as_view(), name="privacy-consent"),
    path(
        "privacy/food-photos/<uuid:scan_id>/",
        PrivacyFoodPhotoDeleteView.as_view(),
        name="privacy-food-photo-delete",
    ),
    path(
        "privacy/ai-chat-history/",
        PrivacyAIChatHistoryDeleteView.as_view(),
        name="privacy-ai-chat-history-delete",
    ),
    path("privacy/account/", PrivacyAccountDeleteView.as_view(), name="privacy-account-delete"),
]
