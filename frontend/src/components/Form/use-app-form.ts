"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  useForm,
  type FieldValues,
  type UseFormProps,
  type UseFormReturn,
} from "react-hook-form";
import type { z } from "zod";

interface UseAppFormOptions<TFieldValues extends FieldValues> extends Omit<
  UseFormProps<TFieldValues>,
  "resolver"
> {
  schema: z.ZodType<TFieldValues, TFieldValues>;
}

export function useAppForm<TFieldValues extends FieldValues>({
  schema,
  ...formOptions
}: UseAppFormOptions<TFieldValues>): UseFormReturn<TFieldValues> {
  return useForm<TFieldValues>({
    mode: "onBlur",
    reValidateMode: "onChange",
    resolver: zodResolver(schema),
    ...formOptions,
  });
}
