"use client";

import { AlertTriangle, MessageCircle, RefreshCw, Send, ShieldCheck } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LoadingState } from "@/components/ui/loading-state";
import { aiCoachApi } from "@/lib/api/ai-coach";
import { getErrorMessage } from "@/lib/api/errors";
import type { AICoachResponse, AICoachSettings } from "@/lib/api/types";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export function NutritionCoachPanel() {
  const [settings, setSettings] = useState<AICoachSettings | null>(null);
  const [message, setMessage] = useState("");
  const [contextDate, setContextDate] = useState(todayIsoDate());
  const [storeResponse, setStoreResponse] = useState(false);
  const [response, setResponse] = useState<AICoachResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAsking, setIsAsking] = useState(false);
  const [isUpdatingConsent, setIsUpdatingConsent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadSettings() {
    setIsLoading(true);
    setError(null);
    try {
      setSettings(await aiCoachApi.getSettings());
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadSettings();
  }, []);

  async function handleConsentChange(enabled: boolean) {
    setIsUpdatingConsent(true);
    setError(null);
    try {
      const nextSettings = await aiCoachApi.updateHistoryConsent(enabled);
      setSettings(nextSettings);
      if (!nextSettings.chat_history_enabled) {
        setStoreResponse(false);
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsUpdatingConsent(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedMessage = message.trim();
    if (!normalizedMessage) {
      return;
    }

    setIsAsking(true);
    setError(null);
    setResponse(null);
    try {
      setResponse(
        await aiCoachApi.ask({
          message: normalizedMessage,
          date: contextDate,
          store_response: settings?.chat_history_enabled === true && storeResponse,
        }),
      );
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsAsking(false);
    }
  }

  if (isLoading) {
    return <LoadingState label={copy.coach.loading} />;
  }

  if (!settings) {
    return (
      <section className="session-state">
        <p className="form-error" role="alert">{error ?? copy.coach.settingsFailed}</p>
        <Button
          icon={<RefreshCw aria-hidden="true" size={18} />}
          onClick={() => void loadSettings()}
          variant="secondary"
        >
          {copy.common.retry}
        </Button>
      </section>
    );
  }

  return (
    <div className="coach-layout">
      <form className="coach-form" onSubmit={handleSubmit}>
        <label className="field" htmlFor="coach-date">
          <span className="field__label">{copy.coach.date}</span>
          <input
            className="field__input"
            id="coach-date"
            onChange={(event) => setContextDate(event.target.value)}
            type="date"
            value={contextDate}
          />
        </label>

        <label className="field" htmlFor="coach-message">
          <span className="field__label">{copy.coach.message}</span>
          <textarea
            className="field__input coach-textarea"
            id="coach-message"
            maxLength={2000}
            onChange={(event) => setMessage(event.target.value)}
            placeholder={copy.coach.messagePlaceholder}
            required
            value={message}
          />
        </label>

        <section className="coach-consent">
          <ShieldCheck aria-hidden="true" size={22} />
          <div>
            <label className="checkbox-row">
              <input
                checked={settings.chat_history_enabled}
                disabled={isUpdatingConsent}
                onChange={(event) => void handleConsentChange(event.target.checked)}
                type="checkbox"
              />
              <span>{copy.coach.historyConsent}</span>
            </label>
            <p>{copy.coach.historyConsentHint}</p>
            {settings.chat_history_enabled ? (
              <label className="checkbox-row coach-store-response">
                <input
                  checked={storeResponse}
                  onChange={(event) => setStoreResponse(event.target.checked)}
                  type="checkbox"
                />
                <span>{copy.coach.storeThisResponse}</span>
              </label>
            ) : null}
          </div>
        </section>

        {error ? <p className="form-error" role="alert">{error}</p> : null}
        <Button
          disabled={isAsking || message.trim().length === 0}
          icon={<Send aria-hidden="true" size={18} />}
          type="submit"
        >
          {isAsking ? copy.coach.asking : copy.coach.askAction}
        </Button>
      </form>

      {isAsking ? <LoadingState label={copy.coach.processing} /> : null}
      {response ? <CoachResponse response={response} /> : null}
      {!isAsking && !response ? (
        <Card className="coach-empty">
          <MessageCircle aria-hidden="true" size={28} />
          <h2>{copy.coach.emptyTitle}</h2>
          <p>{copy.coach.emptyDescription}</p>
        </Card>
      ) : null}
    </div>
  );
}

function CoachResponse({ response }: { response: AICoachResponse }) {
  return (
    <article className={response.safety.blocked ? "coach-response coach-response--blocked" : "coach-response"}>
      <header>
        {response.safety.blocked ? (
          <AlertTriangle aria-hidden="true" size={24} />
        ) : (
          <MessageCircle aria-hidden="true" size={24} />
        )}
        <div>
          <span>{copy.coach.responseFor} {response.context_date}</span>
          <h2>{response.safety.blocked ? copy.coach.safetyTitle : copy.coach.responseTitle}</h2>
        </div>
      </header>
      <p className="coach-answer">{response.answer}</p>

      {response.suggestions.length > 0 ? (
        <ResponseList title={copy.coach.suggestions} values={response.suggestions} />
      ) : null}
      {response.nutrition_notes.length > 0 ? (
        <ResponseList
          title={copy.coach.nutritionNotes}
          values={response.nutrition_notes.map((note) => note.message)}
        />
      ) : null}
      {response.warnings.length > 0 ? (
        <ResponseList title={copy.coach.warnings} values={response.warnings} />
      ) : null}
      <small>{response.stored ? copy.coach.responseStored : copy.coach.responseNotStored}</small>
    </article>
  );
}

function ResponseList({ title, values }: { title: string; values: string[] }) {
  return (
    <section className="coach-response__section">
      <h3>{title}</h3>
      <ul>
        {values.map((value, index) => <li key={`${index}-${value}`}>{value}</li>)}
      </ul>
    </section>
  );
}

function todayIsoDate(): string {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}
