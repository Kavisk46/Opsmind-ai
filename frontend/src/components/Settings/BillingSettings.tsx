"use client";

import { CreditCard, Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { formatDate } from "@/lib/format";
import billingPlanData from "@/lib/mock-data/admin-billing-plan.json";
import invoicesData from "@/lib/mock-data/admin-invoices.json";
import { toast } from "@/lib/toast";

import { AdminStatusBadge } from "./AdminStatusBadge";
import { SettingsEmptyState } from "./SettingsEmptyState";
import { SettingsPageSkeleton } from "./SettingsPageSkeleton";

interface BillingPlan {
  planName: string;
  priceLabel: string;
  renewalDate: string;
  cardBrand: string;
  cardLast4: string;
  cardExpiry: string;
}

interface Invoice {
  id: string;
  date: string;
  amount: string;
  status: "paid" | "pending" | "failed";
}

const plan = billingPlanData as BillingPlan;
const invoices = invoicesData as Invoice[];

const INVOICE_STATUS_VARIANT: Record<
  Invoice["status"],
  "success" | "warning" | "destructive"
> = {
  paid: "success",
  pending: "warning",
  failed: "destructive",
};

const INVOICE_STATUS_LABEL: Record<Invoice["status"], string> = {
  paid: "Paid",
  pending: "Pending",
  failed: "Failed",
};

export function BillingSettings() {
  const isLoading = useSimulatedLoad();

  if (isLoading) {
    return <SettingsPageSkeleton />;
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle level="h2">Current plan</CardTitle>
          <CardDescription>
            Your subscription and billing cycle.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-lg font-semibold text-foreground">
              {plan.planName}
            </p>
            <p className="text-sm text-muted-foreground">
              {plan.priceLabel} · Renews{" "}
              {formatDate(plan.renewalDate, {
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              toast("Plan changes aren't available in this preview.")
            }
          >
            Change plan
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle level="h2">Payment method</CardTitle>
          <CardDescription>
            Used for your subscription charges.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-12 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-muted-foreground">
              <CreditCard className="h-4 w-4" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">
                {plan.cardBrand} •••• {plan.cardLast4}
              </p>
              <p className="text-xs text-muted-foreground">
                Expires {plan.cardExpiry}
              </p>
            </div>
          </div>
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              toast("Payment method updates aren't available in this preview.")
            }
          >
            Update
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle level="h2">Invoice history</CardTitle>
          <CardDescription>Past invoices for your subscription.</CardDescription>
        </CardHeader>
        <CardContent>
          {invoices.length === 0 ? (
            <SettingsEmptyState
              title="No invoices yet"
              description="Your invoices will appear here after your first billing cycle."
            />
          ) : (
            <Table>
              <TableCaption>Invoice history</TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead>Invoice</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices.map((invoice) => (
                  <TableRow key={invoice.id}>
                    <TableCell className="font-mono text-xs whitespace-nowrap">
                      {invoice.id}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-muted-foreground">
                      {formatDate(invoice.date, {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-foreground">
                      {invoice.amount}
                    </TableCell>
                    <TableCell>
                      <AdminStatusBadge
                        label={INVOICE_STATUS_LABEL[invoice.status]}
                        variant={INVOICE_STATUS_VARIANT[invoice.status]}
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          toast(
                            "Invoice downloads aren't available in this preview."
                          )
                        }
                        className="gap-1.5"
                      >
                        <Download className="h-3.5 w-3.5" aria-hidden="true" />
                        Download
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
