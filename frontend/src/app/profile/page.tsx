import { ShieldCheck } from "lucide-react";

import { AppShell } from "@/components/app-shell";
import { PageHeading } from "@/components/page-heading";
import { Card } from "@/components/ui/card";
import { SelectField } from "@/components/ui/select-field";
import { TextField } from "@/components/ui/text-field";
import { messages } from "@/lib/i18n/messages";

const copy = messages.ru;

export default function ProfilePage() {
  return (
    <AppShell>
      <PageHeading title={copy.profile.title} subtitle={copy.profile.subtitle} />

      <section className="profile-grid">
        <Card className="panel">
          <div className="form-grid">
            <SelectField
              label={copy.profile.goal}
              name="goal"
              options={[
                { value: "maintain", label: "Поддержание" },
                { value: "lose_weight", label: "Снижение массы" },
                { value: "gain_weight", label: "Набор массы" },
              ]}
            />
            <TextField inputMode="decimal" label={copy.profile.height} name="height" />
            <TextField inputMode="decimal" label={copy.profile.mass} name="mass" />
            <SelectField
              label={copy.profile.activity}
              name="activity"
              options={[
                { value: "low", label: "Низкая" },
                { value: "moderate", label: "Средняя" },
                { value: "high", label: "Высокая" },
              ]}
            />
          </div>
        </Card>

        <Card className="consent-panel">
          <ShieldCheck aria-hidden="true" size={26} strokeWidth={1.9} />
          <div>
            <h2>{copy.profile.consent}</h2>
            <p>{copy.auth.sessionCookieNote}</p>
          </div>
        </Card>
      </section>
    </AppShell>
  );
}
