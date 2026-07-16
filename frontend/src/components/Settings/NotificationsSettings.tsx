"use client";

import { Form, useAppForm } from "@/components/Form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useSimulatedLoad } from "@/hooks/use-simulated-load";
import notificationsData from "@/lib/mock-data/settings-notifications.json";

import {
  notificationsFormSchema,
  type NotificationsFormValues,
} from "./settings-schemas";
import { SettingsEmptyState } from "./SettingsEmptyState";
import { SettingsFormActions } from "./SettingsFormActions";
import { SettingsPageSkeleton } from "./SettingsPageSkeleton";
import { useSettingsSave } from "./use-settings-save";

const defaultNotifications = notificationsData as NotificationsFormValues;
// Row structure (id/label/description) is static — only the checked state
// is reactive, and that's managed uncontrolled via RHF's register(), so
// mapping over the static list (not form.watch()) avoids re-rendering the
// whole table on every single toggle.
const categories = defaultNotifications.categories;

export function NotificationsSettings() {
  const isLoading = useSimulatedLoad();
  const { status, errorMessage, save } = useSettingsSave();

  const form = useAppForm({
    schema: notificationsFormSchema,
    defaultValues: defaultNotifications,
  });

  if (isLoading) {
    return <SettingsPageSkeleton />;
  }

  if (categories.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle level="h2">Notifications</CardTitle>
          <CardDescription>
            Choose what you&apos;re notified about and how.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <SettingsEmptyState
            title="No notification categories yet"
            description="Notification preferences will appear here once they&apos;re configured."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle level="h2">Notifications</CardTitle>
        <CardDescription>
          Choose what you&apos;re notified about and how.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form form={form} onSubmit={save} className="space-y-5">
          <Table>
            <TableCaption>
              Notification preferences by category and channel
            </TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead>Category</TableHead>
                <TableHead className="text-center">Email</TableHead>
                <TableHead className="text-center">Push</TableHead>
                <TableHead className="text-center">In-app</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {categories.map((category, index) => (
                <TableRow key={category.id}>
                  <th
                    scope="row"
                    className="px-3 py-2.5 text-left align-middle font-normal text-foreground"
                  >
                    <p className="font-medium text-foreground">
                      {category.label}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {category.description}
                    </p>
                  </th>
                  <TableCell className="text-center">
                    <Switch
                      aria-label={`Email notifications for ${category.label}`}
                      {...form.register(`categories.${index}.email`)}
                    />
                  </TableCell>
                  <TableCell className="text-center">
                    <Switch
                      aria-label={`Push notifications for ${category.label}`}
                      {...form.register(`categories.${index}.push`)}
                    />
                  </TableCell>
                  <TableCell className="text-center">
                    <Switch
                      aria-label={`In-app notifications for ${category.label}`}
                      {...form.register(`categories.${index}.inApp`)}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

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
