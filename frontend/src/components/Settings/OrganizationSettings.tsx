"use client";

import { Globe } from "lucide-react";

import { Form, useAppForm } from "@/components/Form";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useSimulatedLoad } from "@/hooks/use-simulated-load";
import organizationData from "@/lib/mock-data/settings-organization.json";

import {
  organizationFormSchema,
  type OrganizationFormValues,
} from "./settings-schemas";
import { SettingsEmptyState } from "./SettingsEmptyState";
import { SettingsField } from "./SettingsField";
import { SettingsFormActions } from "./SettingsFormActions";
import { SettingsPageSkeleton } from "./SettingsPageSkeleton";
import { SettingsSelectField } from "./SettingsSelectField";
import { useSettingsSave } from "./use-settings-save";

const defaultOrganization = organizationData as OrganizationFormValues & {
  domains: string[];
};
const { domains } = defaultOrganization;

const INDUSTRY_OPTIONS = [
  { value: "Software & Technology", label: "Software & Technology" },
  { value: "Financial Services", label: "Financial Services" },
  { value: "Healthcare", label: "Healthcare" },
  { value: "Retail & E-commerce", label: "Retail & E-commerce" },
  { value: "Education", label: "Education" },
  { value: "Other", label: "Other" },
];

const SIZE_OPTIONS = [
  { value: "1-10 employees", label: "1-10 employees" },
  { value: "11-50 employees", label: "11-50 employees" },
  { value: "51-200 employees", label: "51-200 employees" },
  { value: "201-500 employees", label: "201-500 employees" },
  { value: "500+ employees", label: "500+ employees" },
];

const TIMEZONE_OPTIONS = [
  { value: "America/Los_Angeles", label: "Pacific Time (US & Canada)" },
  { value: "America/Denver", label: "Mountain Time (US & Canada)" },
  { value: "America/Chicago", label: "Central Time (US & Canada)" },
  { value: "America/New_York", label: "Eastern Time (US & Canada)" },
  { value: "Europe/London", label: "London" },
  { value: "Europe/Berlin", label: "Berlin" },
  { value: "Asia/Tokyo", label: "Tokyo" },
];

export function OrganizationSettings() {
  const isLoading = useSimulatedLoad();
  const { status, errorMessage, save } = useSettingsSave();

  const form = useAppForm({
    schema: organizationFormSchema,
    defaultValues: defaultOrganization,
  });

  if (isLoading) {
    return <SettingsPageSkeleton />;
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle level="h2">Organization</CardTitle>
          <CardDescription>
            Your company&apos;s identity and default workspace settings.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form form={form} onSubmit={save} className="space-y-5">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <SettingsField
                name="name"
                label="Organization name"
                autoComplete="organization"
                required
              />
              <SettingsField
                name="domain"
                label="Primary domain"
                hint="Used for suggested teammate invites."
              />
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <SettingsSelectField
                name="industry"
                label="Industry"
                options={INDUSTRY_OPTIONS}
              />
              <SettingsSelectField
                name="size"
                label="Company size"
                options={SIZE_OPTIONS}
              />
            </div>
            <SettingsSelectField
              name="timezone"
              label="Default timezone"
              options={TIMEZONE_OPTIONS}
              hint="Applied to new team members by default."
              required
            />

            <SettingsFormActions
              status={status}
              errorMessage={errorMessage}
              disabled={form.formState.isSubmitting}
            />
          </Form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle level="h2">Connected domains</CardTitle>
          <CardDescription>
            Verified domains let teammates join automatically with a matching
            email address.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {domains.length === 0 ? (
            <SettingsEmptyState
              icon={Globe}
              title="No domains connected"
              description="Verify a company domain so teammates can join automatically."
            />
          ) : (
            <ul className="divide-y divide-border rounded-md border border-border">
              {domains.map((domain) => (
                <li
                  key={domain}
                  className="flex items-center justify-between px-3 py-2 text-sm"
                >
                  <span className="text-foreground">{domain}</span>
                  <Badge variant="success">Verified</Badge>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
