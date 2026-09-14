"use client";

import { RefreshCw, Save, ShieldCheck } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LoadingState } from "@/components/ui/loading-state";
import { SelectField } from "@/components/ui/select-field";
import { TextField } from "@/components/ui/text-field";
import { getErrorMessage } from "@/lib/api/errors";
import { profileApi } from "@/lib/api/profile";
import type { NutritionProfile } from "@/lib/api/types";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;
const CENTIMETERS_PER_INCH = 2.54;
const POUNDS_PER_KILOGRAM = 2.2046226218;

type ProfileDraft = {
  goal: string;
  heightCm: string;
  massKg: string;
  ageCategory: string;
  activityLevel: string;
  preferredUnits: string;
  dietaryPreferences: string[];
};

const GOAL_OPTIONS = [
  { value: "maintain_weight", label: "Поддержание массы" },
  { value: "lose_weight", label: "Снижение массы" },
  { value: "gain_weight", label: "Набор массы" },
  { value: "improve_habits", label: "Улучшение пищевых привычек" },
];

const AGE_OPTIONS = [
  { value: "prefer_not_to_say", label: "Предпочитаю не указывать" },
  { value: "under_18", label: "До 18 лет" },
  { value: "18_29", label: "18–29 лет" },
  { value: "30_39", label: "30–39 лет" },
  { value: "40_49", label: "40–49 лет" },
  { value: "50_64", label: "50–64 года" },
  { value: "65_plus", label: "65 лет и старше" },
];

const ACTIVITY_OPTIONS = [
  { value: "sedentary", label: "Малоподвижный образ жизни" },
  { value: "light", label: "Лёгкая активность" },
  { value: "moderate", label: "Умеренная активность" },
  { value: "active", label: "Высокая активность" },
  { value: "very_active", label: "Очень высокая активность" },
];

const UNIT_OPTIONS = [
  { value: "metric", label: "Метрические (см, кг)" },
  { value: "imperial", label: "Имперские (дюймы, фунты)" },
];

const DIETARY_OPTIONS = [
  { value: "vegetarian", label: "Вегетарианство" },
  { value: "vegan", label: "Веганство" },
  { value: "pescatarian", label: "Пескетарианство" },
  { value: "halal", label: "Халяль" },
  { value: "kosher", label: "Кошерное питание" },
  { value: "high_protein", label: "Повышенное содержание белка" },
  { value: "low_carb", label: "Низкое содержание углеводов" },
];

export function NutritionProfileForm() {
  const [profile, setProfile] = useState<NutritionProfile | null>(null);
  const [draft, setDraft] = useState<ProfileDraft | null>(null);
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function loadProfile() {
    setIsLoading(true);
    setError(null);
    try {
      const result = await profileApi.getCurrentNutritionProfile();
      setProfile(result);
      setDraft(toDraft(result));
      setConsentAccepted(result.consent_granted_at !== null);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadProfile();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile || !draft) {
      return;
    }

    setIsSaving(true);
    setError(null);
    setSaved(false);
    try {
      const result = await profileApi.updateNutritionProfile(profile.id, {
        goal: draft.goal,
        height_cm: toMetricHeight(draft.heightCm, draft.preferredUnits),
        mass_kg: toMetricMass(draft.massKg, draft.preferredUnits),
        age_category: draft.ageCategory,
        activity_level: draft.activityLevel,
        preferred_units: draft.preferredUnits,
        dietary_preferences: draft.dietaryPreferences,
        consent_accepted: profile.consent_granted_at !== null || consentAccepted,
      });
      setProfile(result);
      setDraft(toDraft(result));
      setConsentAccepted(result.consent_granted_at !== null);
      setSaved(true);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return <LoadingState label={copy.profile.loading} />;
  }

  if (!profile || !draft) {
    return (
      <section className="session-state">
        <p className="form-error" role="alert">{error ?? copy.profile.loadFailed}</p>
        <Button
          icon={<RefreshCw aria-hidden="true" size={18} />}
          onClick={() => void loadProfile()}
          variant="secondary"
        >
          {copy.common.retry}
        </Button>
      </section>
    );
  }

  const consentRequired = profile.consent_granted_at === null;

  return (
    <form className="profile-grid" onSubmit={handleSubmit}>
      <Card className="panel profile-form-panel">
        <div className="form-grid">
          <SelectField label={copy.profile.goal} name="goal" onChange={(event) => setDraft({ ...draft, goal: event.target.value })} options={GOAL_OPTIONS} value={draft.goal} />
          <SelectField label={copy.profile.ageCategory} name="age_category" onChange={(event) => setDraft({ ...draft, ageCategory: event.target.value })} options={AGE_OPTIONS} value={draft.ageCategory} />
          <TextField inputMode="decimal" label={draft.preferredUnits === "imperial" ? copy.profile.heightImperial : copy.profile.height} max={draft.preferredUnits === "imperial" ? 98 : 250} min={draft.preferredUnits === "imperial" ? 31 : 80} name="height" onChange={(event) => setDraft({ ...draft, heightCm: event.target.value })} placeholder={draft.preferredUnits === "imperial" ? "67" : "170"} step="0.01" type="number" value={draft.heightCm} />
          <TextField inputMode="decimal" label={draft.preferredUnits === "imperial" ? copy.profile.massImperial : copy.profile.mass} max={draft.preferredUnits === "imperial" ? 882 : 400} min={draft.preferredUnits === "imperial" ? 44 : 20} name="mass" onChange={(event) => setDraft({ ...draft, massKg: event.target.value })} placeholder={draft.preferredUnits === "imperial" ? "154.32" : "70.00"} step="0.01" type="number" value={draft.massKg} />
          <SelectField label={copy.profile.activity} name="activity_level" onChange={(event) => setDraft({ ...draft, activityLevel: event.target.value })} options={ACTIVITY_OPTIONS} value={draft.activityLevel} />
          <SelectField label={copy.profile.units} name="preferred_units" onChange={(event) => setDraft(convertUnits(draft, event.target.value))} options={UNIT_OPTIONS} value={draft.preferredUnits} />
        </div>

        <fieldset className="preference-fieldset">
          <legend>{copy.profile.dietaryPreferences}</legend>
          <p>{copy.profile.dietaryPreferencesHint}</p>
          <div className="preference-grid">
            {DIETARY_OPTIONS.map((option) => (
              <label className="checkbox-row" key={option.value}>
                <input
                  checked={draft.dietaryPreferences.includes(option.value)}
                  onChange={(event) => {
                    const next = event.target.checked
                      ? [...draft.dietaryPreferences, option.value]
                      : draft.dietaryPreferences.filter((value) => value !== option.value);
                    setDraft({ ...draft, dietaryPreferences: next });
                  }}
                  type="checkbox"
                  value={option.value}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </fieldset>
      </Card>

      <section className="consent-panel">
        <ShieldCheck aria-hidden="true" size={26} strokeWidth={1.9} />
        <div>
          <h2>{copy.profile.consent}</h2>
          <p>{copy.profile.consentDescription}</p>
          {consentRequired ? (
            <label className="checkbox-row checkbox-row--consent">
              <input checked={consentAccepted} onChange={(event) => setConsentAccepted(event.target.checked)} required type="checkbox" />
              <span>{copy.profile.consentAction}</span>
            </label>
          ) : (
            <p className="form-success">{copy.profile.consentGranted}</p>
          )}
        </div>
      </section>

      {error ? <p className="form-error" role="alert">{error}</p> : null}
      {saved ? <p className="form-success" role="status">{copy.profile.saved}</p> : null}
      <div className="profile-form-actions">
        <Button disabled={isSaving || (consentRequired && !consentAccepted)} icon={<Save aria-hidden="true" size={18} />} type="submit">
          {isSaving ? copy.common.saving : copy.common.save}
        </Button>
      </div>
    </form>
  );
}

function toDraft(profile: NutritionProfile): ProfileDraft {
  const isImperial = profile.preferred_units === "imperial";
  return {
    goal: profile.goal,
    heightCm:
      profile.height_cm === null
        ? ""
        : isImperial
          ? formatDecimal(profile.height_cm / CENTIMETERS_PER_INCH)
          : String(profile.height_cm),
    massKg:
      profile.mass_kg === null
        ? ""
        : isImperial
          ? formatDecimal(Number(profile.mass_kg) * POUNDS_PER_KILOGRAM)
          : profile.mass_kg,
    ageCategory: profile.age_category,
    activityLevel: profile.activity_level,
    preferredUnits: profile.preferred_units,
    dietaryPreferences: profile.dietary_preferences.filter((value) => value !== "none"),
  };
}

function convertUnits(draft: ProfileDraft, nextUnits: string): ProfileDraft {
  if (draft.preferredUnits === nextUnits) {
    return draft;
  }

  const toImperial = nextUnits === "imperial";
  return {
    ...draft,
    preferredUnits: nextUnits,
    heightCm: convertOptionalDecimal(
      draft.heightCm,
      toImperial ? (value) => value / CENTIMETERS_PER_INCH : (value) => value * CENTIMETERS_PER_INCH,
    ),
    massKg: convertOptionalDecimal(
      draft.massKg,
      toImperial ? (value) => value * POUNDS_PER_KILOGRAM : (value) => value / POUNDS_PER_KILOGRAM,
    ),
  };
}

function toMetricHeight(value: string, units: string): number | null {
  if (value === "") {
    return null;
  }
  const height = Number(value);
  return Number(formatDecimal(units === "imperial" ? height * CENTIMETERS_PER_INCH : height));
}

function toMetricMass(value: string, units: string): string | null {
  if (value === "") {
    return null;
  }
  if (units !== "imperial") {
    return value;
  }
  const mass = Number(value);
  return formatDecimal(mass / POUNDS_PER_KILOGRAM);
}

function convertOptionalDecimal(value: string, converter: (numberValue: number) => number): string {
  return value === "" ? "" : formatDecimal(converter(Number(value)));
}

function formatDecimal(value: number): string {
  return value.toFixed(2).replace(/\.00$/, "");
}
