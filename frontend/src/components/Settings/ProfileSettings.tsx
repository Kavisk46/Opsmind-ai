"use client";

import { Form, useAppForm } from "@/components/Form";
import { Avatar } from "@/components/ui/avatar";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useSimulatedLoad } from "@/hooks/use-simulated-load";
import profileData from "@/lib/mock-data/settings-profile.json";

import { profileFormSchema, type ProfileFormValues } from "./settings-schemas";
import { SettingsField } from "./SettingsField";
import { SettingsFormActions } from "./SettingsFormActions";
import { SettingsPageSkeleton } from "./SettingsPageSkeleton";
import { SettingsTextareaField } from "./SettingsTextareaField";
import { useSettingsSave } from "./use-settings-save";

const defaultProfile = profileData as ProfileFormValues;

export function ProfileSettings() {
  const isLoading = useSimulatedLoad();
  const { status, errorMessage, save } = useSettingsSave();

  const form = useAppForm({
    schema: profileFormSchema,
    defaultValues: defaultProfile,
  });

  if (isLoading) {
    return <SettingsPageSkeleton />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle level="h2">Profile</CardTitle>
        <CardDescription>
          Your personal information and public profile.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form form={form} onSubmit={save} className="space-y-5">
          <div className="flex items-center gap-4">
            <Avatar name={form.watch("name")} size={56} />
            <div>
              <p className="text-sm font-medium text-foreground">
                Profile photo
              </p>
              <p className="text-xs text-muted-foreground">
                Generated from your name — photo upload isn&apos;t available
                in this preview.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SettingsField
              name="name"
              label="Full name"
              autoComplete="name"
              required
            />
            <SettingsField
              name="email"
              label="Email"
              type="email"
              autoComplete="email"
              required
            />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SettingsField
              name="jobTitle"
              label="Job title"
              autoComplete="organization-title"
            />
            <SettingsField
              name="phone"
              label="Phone"
              type="tel"
              autoComplete="tel"
              hint="Optional — used for account recovery only."
            />
          </div>
          <SettingsTextareaField
            name="bio"
            label="Bio"
            hint="A short description shown on your profile."
          />

          <SettingsFormActions
            status={status}
            errorMessage={errorMessage}
            disabled={form.formState.isSubmitting}
          />
        </Form>
      </CardContent>
    </Card>
  );
}
