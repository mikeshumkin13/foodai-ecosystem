"use client";

import { Camera, RefreshCw, RotateCw, Upload } from "lucide-react";
import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { foodsApi } from "@/lib/api/foods";
import { scansApi } from "@/lib/api/scans";
import type { FoodScanDetectedItem, FoodScanResult, FoodSearchItem } from "@/lib/api/types";
import { getErrorMessage } from "@/lib/api/errors";
import { messages } from "@/lib/i18n/messages";
import { cn } from "@/lib/utils";

import { ScanDetectedItemCard } from "./scan-detected-item-card";
import { getMassDraftValue } from "./scan-format";
import { ScanReviewSummary } from "./scan-review-summary";

type UploadMode = "file" | "camera";

const copy = messages.ru;
const pollingStatuses = new Set(["uploaded", "processing"]);

export function ScanUploadPanel() {
  const router = useRouter();
  const [uploadMode, setUploadMode] = useState<UploadMode>("file");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [scanId, setScanId] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<FoodScanResult | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [savingItemId, setSavingItemId] = useState<string | null>(null);
  const [searchingItemId, setSearchingItemId] = useState<string | null>(null);
  const [isSearchingAddFood, setIsSearchingAddFood] = useState(false);
  const [isAddingItem, setIsAddingItem] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [massDrafts, setMassDrafts] = useState<Record<string, string>>({});
  const [foodQueries, setFoodQueries] = useState<Record<string, string>>({});
  const [foodOptions, setFoodOptions] = useState<Record<string, FoodSearchItem[]>>({});
  const [addQuery, setAddQuery] = useState("");
  const [addOptions, setAddOptions] = useState<FoodSearchItem[]>([]);
  const [selectedAddFoodId, setSelectedAddFoodId] = useState("");
  const [addMass, setAddMass] = useState("100");
  const [mealType, setMealType] = useState("breakfast");
  const [loggedAt, setLoggedAt] = useState(getDefaultLoggedAt());
  const [error, setError] = useState<string | null>(null);

  const activeItems = useMemo(
    () => scanResult?.detected_items.filter((item) => !item.is_removed) ?? [],
    [scanResult],
  );
  const canConfirm =
    scanResult?.status === "needs_confirmation" &&
    activeItems.length > 0 &&
    activeItems.every((item) => item.food_id);
  const shouldPoll = Boolean(scanId && (!scanResult || pollingStatuses.has(scanResult.status)));

  useEffect(() => {
    if (!scanId || !shouldPoll) {
      return undefined;
    }

    let isActive = true;
    const activeScanId = scanId;

    async function loadResult() {
      setIsPolling(true);
      try {
        const result = await scansApi.result(activeScanId);
        if (isActive) {
          setScanResult(result);
          syncMassDrafts(result.detected_items);
          setError(null);
        }
      } catch (requestError) {
        if (isActive) {
          setError(getErrorMessage(requestError));
        }
      } finally {
        if (isActive) {
          setIsPolling(false);
        }
      }
    }

    void loadResult();
    const intervalId = window.setInterval(loadResult, 2500);

    return () => {
      isActive = false;
      window.clearInterval(intervalId);
    };
  }, [scanId, shouldPoll]);

  function syncMassDrafts(items: FoodScanDetectedItem[]) {
    setMassDrafts((currentDrafts) => {
      const nextDrafts = { ...currentDrafts };
      for (const item of items) {
        nextDrafts[item.id] ??= getMassDraftValue(item);
      }
      return nextDrafts;
    });
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFile(event.target.files?.[0] ?? null);
    setScanResult(null);
    setScanId(null);
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) {
      return;
    }

    setIsUploading(true);
    setError(null);
    setScanResult(null);

    try {
      const response = await scansApi.upload(selectedFile);
      setScanId(response.scan_id);
      setScanResult({
        id: response.scan_id,
        user_id: "",
        status: response.status,
        failure_code: "",
        confirmed_meal_id: null,
        image_format: "",
        content_type: selectedFile.type,
        uploaded_byte_size: selectedFile.size,
        stored_byte_size: 0,
        width: 0,
        height: 0,
        exif_stripped: false,
        created_at: "",
        updated_at: "",
        detected_items: [],
      });
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsUploading(false);
    }
  }

  async function handleRefreshResult() {
    if (!scanId) {
      return;
    }

    setIsPolling(true);
    setError(null);
    try {
      const result = await scansApi.result(scanId);
      setScanResult(result);
      syncMassDrafts(result.detected_items);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsPolling(false);
    }
  }

  async function handleRetry() {
    if (!scanId) {
      return;
    }

    setError(null);
    try {
      const response = await scansApi.retry(scanId);
      setScanResult((currentResult) =>
        currentResult
          ? { ...currentResult, status: response.status, failure_code: "", detected_items: [] }
          : currentResult,
      );
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  }

  async function handleSaveMass(item: FoodScanDetectedItem) {
    if (!scanId) {
      return;
    }

    const mass_g = massDrafts[item.id] ?? item.mass_g;
    setSavingItemId(item.id);
    setError(null);

    try {
      const updatedItem = await scansApi.updateItem(scanId, item.id, { mass_g });
      replaceDetectedItem(updatedItem);
      setMassDrafts((currentDrafts) => ({ ...currentDrafts, [updatedItem.id]: getMassDraftValue(updatedItem) }));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSavingItemId(null);
    }
  }

  async function handleFoodSearch(item: FoodScanDetectedItem) {
    const query = foodQueries[item.id]?.trim() ?? "";
    if (query.length < 2) {
      return;
    }

    setSearchingItemId(item.id);
    setError(null);
    try {
      const results = await foodsApi.search(query);
      setFoodOptions((currentOptions) => ({ ...currentOptions, [item.id]: results }));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSearchingItemId(null);
    }
  }

  async function handleSelectFood(item: FoodScanDetectedItem, food: FoodSearchItem) {
    if (!scanId) {
      return;
    }

    setSavingItemId(item.id);
    setError(null);
    try {
      const updatedItem = await scansApi.updateItem(scanId, item.id, {
        food_id: food.id,
        mass_g: massDrafts[item.id] ?? item.mass_g,
      });
      replaceDetectedItem(updatedItem);
      setFoodOptions((currentOptions) => ({ ...currentOptions, [item.id]: [] }));
      setFoodQueries((currentQueries) => ({ ...currentQueries, [item.id]: "" }));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSavingItemId(null);
    }
  }

  async function handleRemoveItem(item: FoodScanDetectedItem) {
    if (!scanId) {
      return;
    }

    setSavingItemId(item.id);
    setError(null);
    try {
      await scansApi.removeItem(scanId, item.id);
      setScanResult((currentResult) =>
        currentResult
          ? {
              ...currentResult,
              detected_items: currentResult.detected_items.map((detectedItem) =>
                detectedItem.id === item.id ? { ...detectedItem, is_removed: true } : detectedItem,
              ),
            }
          : currentResult,
      );
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSavingItemId(null);
    }
  }

  async function handleSearchAddFood() {
    const query = addQuery.trim();
    if (query.length < 2) {
      return;
    }

    setIsSearchingAddFood(true);
    setError(null);
    try {
      const results = await foodsApi.search(query);
      setAddOptions(results);
      setSelectedAddFoodId(results[0]?.id ?? "");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsSearchingAddFood(false);
    }
  }

  async function handleAddItem() {
    if (!scanId || !selectedAddFoodId || !addMass) {
      return;
    }

    setIsAddingItem(true);
    setError(null);
    try {
      const addedItem = await scansApi.addItem(scanId, {
        food_id: selectedAddFoodId,
        mass_g: addMass,
        label: addQuery.trim() || undefined,
      });
      setScanResult((currentResult) =>
        currentResult
          ? { ...currentResult, detected_items: [...currentResult.detected_items, addedItem] }
          : currentResult,
      );
      setMassDrafts((currentDrafts) => ({ ...currentDrafts, [addedItem.id]: getMassDraftValue(addedItem) }));
      setAddQuery("");
      setAddOptions([]);
      setSelectedAddFoodId("");
      setAddMass("100");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsAddingItem(false);
    }
  }

  async function handleConfirm() {
    if (!scanId) {
      return;
    }

    setIsConfirming(true);
    setError(null);
    try {
      const response = await scansApi.confirm(scanId, {
        meal_type: mealType,
        logged_at: toIsoString(loggedAt),
      });
      setScanResult(response.food_scan);
      router.push(`/diary?date=${encodeURIComponent(getDiaryDate(loggedAt))}`);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsConfirming(false);
    }
  }

  function replaceDetectedItem(updatedItem: FoodScanDetectedItem) {
    setScanResult((currentResult) =>
      currentResult
        ? {
            ...currentResult,
            detected_items: currentResult.detected_items.map((item) =>
              item.id === updatedItem.id ? updatedItem : item,
            ),
          }
        : currentResult,
    );
  }

  return (
    <div className="scan-workflow">
      <ol className="scan-steps" aria-label={copy.scan.stepsLabel}>
        {copy.scan.steps.map((step, index) => (
          <li key={step} className={cn(index <= getActiveStepIndex(scanResult) && "scan-steps__item--active")}>
            {step}
          </li>
        ))}
      </ol>

      <div className="scan-panel">
        <form className="upload-form" onSubmit={handleSubmit}>
          <div className="segmented-control" role="group" aria-label={copy.scan.sourceLabel}>
            <button
              className={cn("segmented-control__button", uploadMode === "file" && "segmented-control__button--active")}
              onClick={() => setUploadMode("file")}
              type="button"
            >
              <Upload aria-hidden="true" size={17} />
              <span>{copy.scan.fileMode}</span>
            </button>
            <button
              className={cn("segmented-control__button", uploadMode === "camera" && "segmented-control__button--active")}
              onClick={() => setUploadMode("camera")}
              type="button"
            >
              <Camera aria-hidden="true" size={17} />
              <span>{copy.scan.cameraMode}</span>
            </button>
          </div>

          <label className="upload-dropzone">
            <input
              accept="image/jpeg,image/png"
              aria-label={copy.scan.uploadLabel}
              capture={uploadMode === "camera" ? "environment" : undefined}
              name="photo"
              onChange={handleFileChange}
              type="file"
            />
            <span className="upload-dropzone__icon">
              {uploadMode === "camera" ? (
                <Camera aria-hidden="true" size={24} strokeWidth={1.8} />
              ) : (
                <Upload aria-hidden="true" size={24} strokeWidth={1.8} />
              )}
            </span>
            <span>
              <strong>{copy.scan.uploadLabel}</strong>
              <small>{selectedFile?.name ?? copy.scan.acceptedFormats}</small>
            </span>
          </label>

          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}

          <Button
            disabled={!selectedFile || isUploading}
            icon={<Upload aria-hidden="true" size={18} />}
            type="submit"
          >
            {isUploading ? copy.common.loading : copy.scan.uploadAction}
          </Button>
        </form>

        <section className="scan-result-preview" aria-live="polite">
          {isUploading ? <LoadingState label={copy.common.loading} /> : null}

          {!isUploading && !scanResult ? (
            <EmptyState title={copy.scan.emptyTitle} description={copy.scan.emptyDescription} />
          ) : null}

          {!isUploading && scanResult && pollingStatuses.has(scanResult.status) ? (
            <div className="scan-processing-state">
              <LoadingState label={isPolling ? copy.scan.processingPhoto : copy.scan.waitingProcessing} />
              <strong>{copy.scan.processing}</strong>
              <code>{scanResult.id}</code>
              <Button
                disabled={isPolling}
                icon={<RefreshCw aria-hidden="true" size={18} />}
                onClick={handleRefreshResult}
                variant="secondary"
              >
                {copy.common.refresh}
              </Button>
            </div>
          ) : null}

          {!isUploading && scanResult?.status === "failed" ? (
            <div className="scan-processing-state scan-processing-state--failed">
              <strong>{copy.scan.failedTitle}</strong>
              <span>{scanResult.failure_code || "processing_failed"}</span>
              <Button
                icon={<RotateCw aria-hidden="true" size={18} />}
                onClick={handleRetry}
                variant="secondary"
              >
                {copy.common.retry}
              </Button>
            </div>
          ) : null}

          {!isUploading && scanResult?.status === "confirmed" ? (
            <div className="scan-processing-state">
              <strong>{copy.scan.confirmedTitle}</strong>
              <span>{copy.scan.openingDiary}</span>
            </div>
          ) : null}
        </section>
      </div>

      {scanResult?.status === "needs_confirmation" ? (
        <section className="scan-review-layout" aria-label={copy.scan.reviewLabel}>
          <div className="scan-items-list">
            <div className="scan-section-heading">
              <h2>{copy.scan.reviewTitle}</h2>
              <p>{copy.scan.reviewSubtitle}</p>
            </div>

            {activeItems.length > 0 ? (
              activeItems.map((item) => (
                <ScanDetectedItemCard
                  key={item.id}
                  foodOptions={foodOptions[item.id] ?? []}
                  foodQuery={foodQueries[item.id] ?? ""}
                  isSaving={savingItemId === item.id}
                  isSearching={searchingItemId === item.id}
                  item={item}
                  massDraft={massDrafts[item.id] ?? getMassDraftValue(item)}
                  onFoodQueryChange={(value) =>
                    setFoodQueries((currentQueries) => ({ ...currentQueries, [item.id]: value }))
                  }
                  onFoodSearch={() => void handleFoodSearch(item)}
                  onMassDraftChange={(value) =>
                    setMassDrafts((currentDrafts) => ({ ...currentDrafts, [item.id]: value }))
                  }
                  onRemove={() => void handleRemoveItem(item)}
                  onSaveMass={() => void handleSaveMass(item)}
                  onSelectFood={(food) => void handleSelectFood(item, food)}
                />
              ))
            ) : (
              <EmptyState
                title={copy.scan.noActiveItemsTitle}
                description={copy.scan.noActiveItemsDescription}
              />
            )}
          </div>

          <ScanReviewSummary
            addMass={addMass}
            addOptions={addOptions}
            addQuery={addQuery}
            canConfirm={canConfirm}
            isAddingItem={isAddingItem}
            isConfirming={isConfirming}
            isSearchingAddFood={isSearchingAddFood}
            items={activeItems}
            loggedAt={loggedAt}
            mealType={mealType}
            onAddItem={() => void handleAddItem()}
            onAddMassChange={setAddMass}
            onAddQueryChange={setAddQuery}
            onConfirm={() => void handleConfirm()}
            onLoggedAtChange={setLoggedAt}
            onMealTypeChange={setMealType}
            onSearchAddFood={() => void handleSearchAddFood()}
            onSelectedAddFoodChange={setSelectedAddFoodId}
            selectedAddFoodId={selectedAddFoodId}
          />
        </section>
      ) : null}
    </div>
  );
}

function getActiveStepIndex(result: FoodScanResult | null): number {
  if (!result) {
    return 1;
  }

  if (result.status === "uploaded" || result.status === "processing") {
    return 2;
  }

  if (result.status === "needs_confirmation") {
    return 4;
  }

  if (result.status === "confirmed") {
    return 5;
  }

  return 2;
}

function getDefaultLoggedAt(): string {
  const now = new Date();
  now.setSeconds(0, 0);
  return toDatetimeLocalValue(now);
}

function toDatetimeLocalValue(date: Date): string {
  const timezoneOffsetMs = date.getTimezoneOffset() * 60 * 1000;
  return new Date(date.getTime() - timezoneOffsetMs).toISOString().slice(0, 16);
}

function toIsoString(datetimeLocal: string): string | undefined {
  if (!datetimeLocal) {
    return undefined;
  }

  const parsedDate = new Date(datetimeLocal);
  return Number.isNaN(parsedDate.getTime()) ? undefined : parsedDate.toISOString();
}

function getDiaryDate(datetimeLocal: string): string {
  return datetimeLocal.slice(0, 10) || new Date().toISOString().slice(0, 10);
}
