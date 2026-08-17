"use client";

import { Upload } from "lucide-react";
import { ChangeEvent, FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { scansApi } from "@/lib/api/scans";
import type { FoodScanUploadResponse } from "@/lib/api/types";
import { getErrorMessage } from "@/lib/api/errors";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export function ScanUploadPanel() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<FoodScanUploadResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFile(event.target.files?.[0] ?? null);
    setUploadResult(null);
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) {
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const response = await scansApi.upload(selectedFile);
      setUploadResult(response);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="scan-panel">
      <form className="upload-form" onSubmit={handleSubmit}>
        <label className="upload-dropzone">
          <input
            accept="image/jpeg,image/png"
            aria-label={copy.scan.uploadLabel}
            name="photo"
            onChange={handleFileChange}
            type="file"
          />
          <span className="upload-dropzone__icon">
            <Upload aria-hidden="true" size={24} strokeWidth={1.8} />
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

        {!isUploading && uploadResult ? (
          <div className="scan-result-preview__status">
            <strong>{copy.scan.uploaded}</strong>
            <span>{copy.scan.processing}</span>
            <code>{uploadResult.scan_id}</code>
          </div>
        ) : null}

        {!isUploading && !uploadResult ? (
          <EmptyState title={copy.scan.emptyTitle} description={copy.scan.emptyDescription} />
        ) : null}
      </section>
    </div>
  );
}
