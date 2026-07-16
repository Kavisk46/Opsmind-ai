import { z } from "zod";

import { emailField, optionalString, requiredString } from "@/lib/forms/schemas";
import { isValidPhone } from "@/lib/validation";

export const profileFormSchema = z.object({
  name: requiredString("Name"),
  email: emailField(),
  jobTitle: optionalString(),
  // phoneField() rejects an empty string outright, but this field is
  // optional — reuses the same isValidPhone check, just composed to also
  // accept "unset".
  phone: z
    .string()
    .trim()
    .optional()
    .refine((value) => !value || isValidPhone(value), {
      message: "Enter a valid phone number",
    }),
  bio: optionalString(),
});

export type ProfileFormValues = z.infer<typeof profileFormSchema>;

export const organizationFormSchema = z.object({
  name: requiredString("Organization name"),
  domain: optionalString(),
  industry: optionalString(),
  size: optionalString(),
  timezone: requiredString("Timezone"),
});

export type OrganizationFormValues = z.infer<typeof organizationFormSchema>;

const notificationCategorySchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string(),
  email: z.boolean(),
  push: z.boolean(),
  inApp: z.boolean(),
});

export const notificationsFormSchema = z.object({
  categories: z.array(notificationCategorySchema),
});

export type NotificationsFormValues = z.infer<typeof notificationsFormSchema>;
export type NotificationCategory = z.infer<typeof notificationCategorySchema>;
