"use client";

import {
  Database,
  Download,
  ImageOff,
  MessageSquareOff,
  RefreshCw,
  ShieldCheck,
  Trash2,
  UserX,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { TextField } from "@/components/ui/text-field";
import { getErrorMessage } from "@/lib/api/errors";
import { privacyApi } from "@/lib/api/privacy";
import { scansApi } from "@/lib/api/scans";
import type {
  FoodScanMetadata,
  PrivacyConsentPayload,
  PrivacyDataSummary,
  PrivacySettings,
} from "@/lib/api/types";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export function PrivacyCenterPanel() {
  const router = useRouter();
  const [summary, setSummary] = useState<PrivacyDataSummary | null>(null);
  const [privacySettings, setPrivacySettings] = useState<PrivacySettings | null>(null);
  const [foodScans, setFoodScans] = useState<FoodScanMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [accountPassword, setAccountPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const categoryByCode = useMemo(() => {
    const categories = new Map<string, number>();
    for (const category of summary?.categories ?? []) {
      categories.set(category.code, category.count);
    }
    return categories;
  }, [summary]);

  async function loadPrivacyCenter() {
    setIsLoading(true);
    setError(null);
    try {
      const [summaryResponse, scansResponse] = await Promise.all([
        privacyApi.summary(),
        scansApi.list(),
      ]);
      setSummary(summaryResponse);
      setPrivacySettings(summaryResponse.privacy_settings);
      setFoodScans(scansResponse);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadPrivacyCenter();
  }, []);

  async function updateConsent(payload: PrivacyConsentPayload) {
    setPendingAction("consent");
    setError(null);
    setNotice(null);
    try {
      const updatedSettings = await privacyApi.updateConsent(payload);
      setPrivacySettings(updatedSettings);
      setSummary((currentSummary) =>
        currentSummary ? { ...currentSummary, privacy_settings: updatedSettings } : currentSummary,
      );
      setNotice(copy.privacy.consentSaved);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setPendingAction(null);
    }
  }

  async function handleModelImprovementChange(event: ChangeEvent<HTMLInputElement>) {
    await updateConsent(
      event.target.checked
        ? { model_improvement_consent_accepted: true }
        : { model_improvement_consent_revoked: true },
    );
  }

  async function handleFoodPhotoTrainingChange(event: ChangeEvent<HTMLInputElement>) {
    await updateConsent(
      event.target.checked
        ? { food_photo_training_consent_accepted: true }
        : { food_photo_training_consent_revoked: true },
    );
  }

  async function handleExport() {
    setPendingAction("export");
    setError(null);
    setNotice(null);
    try {
      const exportBlob = await privacyApi.exportData();
      const downloadUrl = URL.createObjectURL(exportBlob);
      const anchor = document.createElement("a");
      anchor.href = downloadUrl;
      anchor.download = "foodai-user-data-export.json";
      anchor.click();
      URL.revokeObjectURL(downloadUrl);
      setNotice(copy.privacy.exportStarted);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setPendingAction(null);
    }
  }

  async function handleDeleteFoodPhoto(scanId: string) {
    if (!window.confirm(copy.privacy.deletePhotoConfirm)) {
      return;
    }

    setPendingAction(scanId);
    setError(null);
    setNotice(null);
    try {
      await privacyApi.deleteFoodPhoto(scanId);
      setFoodScans((currentScans) => currentScans.filter((scan) => scan.id !== scanId));
      setNotice(copy.privacy.photoDeleted);
      await loadPrivacyCenter();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setPendingAction(null);
    }
  }

  async function handleDeleteAiHistory() {
    if (!window.confirm(copy.privacy.deleteAiConfirm)) {
      return;
    }

    setPendingAction("ai-history");
    setError(null);
    setNotice(null);
    try {
      await privacyApi.deleteAiChatHistory();
      setNotice(copy.privacy.aiHistoryDeleted);
      await loadPrivacyCenter();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setPendingAction(null);
    }
  }

  async function handleDeleteAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!window.confirm(copy.privacy.deleteAccountConfirm)) {
      return;
    }

    setPendingAction("account");
    setError(null);
    setNotice(null);
    try {
      await privacyApi.deleteAccount(accountPassword);
      router.replace("/login");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setPendingAction(null);
    }
  }

  const modelImprovementEnabled = privacySettings?.model_improvement_enabled ?? false;
  const foodPhotoTrainingEnabled = privacySettings?.food_photo_training_enabled ?? false;

  return (
    <section className="privacy-layout" aria-label={copy.privacy.title}>
      <div className="toolbar">
        <div>
          {isLoading ? <LoadingState label={copy.common.loading} /> : null}
          {notice ? <p className="form-success">{notice}</p> : null}
          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}
        </div>
        <Button
          disabled={isLoading}
          icon={<RefreshCw aria-hidden="true" size={18} />}
          onClick={() => void loadPrivacyCenter()}
          variant="secondary"
        >
          {copy.common.refresh}
        </Button>
      </div>

      <div className="privacy-grid">
        <Card className="panel privacy-panel">
          <header className="panel__header">
            <h2>{copy.privacy.categoriesTitle}</h2>
            <Database aria-hidden="true" size={22} strokeWidth={1.8} />
          </header>

          {summary ? (
            <div className="privacy-category-list">
              {summary.categories.map((category) => (
                <div className="privacy-category-row" key={category.code}>
                  <div>
                    <strong>{category.label}</strong>
                    <small>{category.storage}</small>
                  </div>
                  <span>{category.count}</span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title={copy.common.empty} description={copy.privacy.emptySummary} />
          )}
        </Card>

        <Card className="panel privacy-panel">
          <header className="panel__header">
            <h2>{copy.privacy.consentTitle}</h2>
            <ShieldCheck aria-hidden="true" size={22} strokeWidth={1.8} />
          </header>

          <div className="consent-list">
            <label className="consent-row">
              <input
                checked={modelImprovementEnabled}
                disabled={pendingAction === "consent"}
                onChange={(event) => void handleModelImprovementChange(event)}
                type="checkbox"
              />
              <span>
                <strong>{copy.privacy.modelImprovement}</strong>
                <small>{copy.privacy.modelImprovementHint}</small>
              </span>
            </label>

            <label className="consent-row">
              <input
                checked={foodPhotoTrainingEnabled}
                disabled={!modelImprovementEnabled || pendingAction === "consent"}
                onChange={(event) => void handleFoodPhotoTrainingChange(event)}
                type="checkbox"
              />
              <span>
                <strong>{copy.privacy.photoTraining}</strong>
                <small>{copy.privacy.photoTrainingHint}</small>
              </span>
            </label>
          </div>
        </Card>

        <Card className="panel privacy-panel">
          <header className="panel__header">
            <h2>{copy.privacy.exportTitle}</h2>
            <Download aria-hidden="true" size={22} strokeWidth={1.8} />
          </header>
          <p className="privacy-copy">{copy.privacy.exportDescription}</p>
          <Button
            disabled={pendingAction === "export"}
            icon={<Download aria-hidden="true" size={18} />}
            onClick={() => void handleExport()}
          >
            {copy.privacy.downloadExport}
          </Button>
        </Card>

        <Card className="panel privacy-panel privacy-panel--wide">
          <header className="panel__header">
            <h2>{copy.privacy.photosTitle}</h2>
            <ImageOff aria-hidden="true" size={22} strokeWidth={1.8} />
          </header>

          {foodScans.length > 0 ? (
            <div className="privacy-scan-list">
              {foodScans.map((scan) => (
                <div className="privacy-scan-row" key={scan.id}>
                  <div>
                    <strong>{scan.image_format}</strong>
                    <small>
                      {new Date(scan.created_at).toLocaleDateString("ru-RU")} · {scan.width}×
                      {scan.height} · {scan.status}
                    </small>
                  </div>
                  <Button
                    disabled={pendingAction === scan.id}
                    icon={<Trash2 aria-hidden="true" size={17} />}
                    onClick={() => void handleDeleteFoodPhoto(scan.id)}
                    variant="ghost"
                  >
                    {copy.privacy.deletePhoto}
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title={copy.common.empty} description={copy.privacy.emptyPhotos} />
          )}
        </Card>

        <Card className="panel privacy-panel privacy-danger">
          <header className="panel__header">
            <h2>{copy.privacy.aiHistoryTitle}</h2>
            <MessageSquareOff aria-hidden="true" size={22} strokeWidth={1.8} />
          </header>
          <p className="privacy-copy">
            {copy.privacy.aiHistoryCount}: {categoryByCode.get("ai_chat_history") ?? 0}
          </p>
          <Button
            disabled={pendingAction === "ai-history"}
            icon={<Trash2 aria-hidden="true" size={17} />}
            onClick={() => void handleDeleteAiHistory()}
            variant="secondary"
          >
            {copy.privacy.deleteAiHistory}
          </Button>
        </Card>

        <Card className="panel privacy-panel privacy-danger">
          <header className="panel__header">
            <h2>{copy.privacy.accountTitle}</h2>
            <UserX aria-hidden="true" size={22} strokeWidth={1.8} />
          </header>
          <form className="privacy-account-form" onSubmit={(event) => void handleDeleteAccount(event)}>
            <p className="privacy-copy">{copy.privacy.accountDescription}</p>
            <TextField
              autoComplete="current-password"
              label={copy.auth.password}
              name="current-password"
              onChange={(event) => setAccountPassword(event.target.value)}
              required
              type="password"
              value={accountPassword}
            />
            <Button
              disabled={pendingAction === "account" || !accountPassword}
              icon={<UserX aria-hidden="true" size={17} />}
              type="submit"
              variant="secondary"
            >
              {copy.privacy.deleteAccount}
            </Button>
          </form>
        </Card>
      </div>
    </section>
  );
}
