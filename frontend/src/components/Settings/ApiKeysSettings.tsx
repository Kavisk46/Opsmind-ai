"use client";

import { Copy, Key, Plus } from "lucide-react";
import { useState } from "react";

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
import { useCopyToClipboard } from "@/hooks/use-copy-to-clipboard";
import { useSimulatedLoad } from "@/hooks/use-simulated-load";
import { formatDate } from "@/lib/format";
import apiKeysData from "@/lib/mock-data/admin-api-keys.json";

import { AdminStatusBadge } from "./AdminStatusBadge";
import { openConfirmDialog } from "./ConfirmDialog";
import { SettingsEmptyState } from "./SettingsEmptyState";
import { SettingsPageSkeleton } from "./SettingsPageSkeleton";

interface ApiKey {
  id: string;
  name: string;
  keyPreview: string;
  createdAt: string;
  lastUsedAt: string | null;
  status: "active" | "revoked";
}

const seedKeys = apiKeysData as ApiKey[];

function formatShortDate(value: string) {
  return formatDate(value, { month: "short", day: "numeric", year: "numeric" });
}

// The "full key" only ever exists client-side for the moment right after
// creation — real APIs never let you see a secret key again after issuing
// it, and this mirrors that even though nothing here is actually persisted.
function generateFakeKey() {
  const random = crypto.randomUUID().replace(/-/g, "").slice(0, 24);
  return {
    fullKey: `sk_live_${random}`,
    preview: `sk_live_••••••••${random.slice(-4)}`,
  };
}

export function ApiKeysSettings() {
  const isLoading = useSimulatedLoad();
  const [keys, setKeys] = useState<ApiKey[]>(seedKeys);
  const [newKey, setNewKey] = useState<{ id: string; fullKey: string } | null>(
    null
  );
  const { copied, copy } = useCopyToClipboard();

  if (isLoading) {
    return <SettingsPageSkeleton />;
  }

  const handleCreate = () => {
    const { fullKey, preview } = generateFakeKey();
    const id = crypto.randomUUID();
    const entry: ApiKey = {
      id,
      name: `New key ${keys.length + 1}`,
      keyPreview: preview,
      createdAt: new Date().toISOString(),
      lastUsedAt: null,
      status: "active",
    };
    setKeys((prev) => [entry, ...prev]);
    setNewKey({ id, fullKey });
  };

  const handleRevoke = (id: string, name: string) => {
    openConfirmDialog({
      title: "Revoke API key?",
      description: `"${name}" will stop working immediately. This can't be undone.`,
      confirmLabel: "Revoke key",
      variant: "destructive",
      onConfirm: () => {
        setKeys((prev) =>
          prev.map((key) =>
            key.id === id ? { ...key, status: "revoked" } : key
          )
        );
        setNewKey((prev) => (prev?.id === id ? null : prev));
      },
    });
  };

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between">
        <div>
          <CardTitle level="h2">API Keys</CardTitle>
          <CardDescription>
            Manage keys used to authenticate API requests.
          </CardDescription>
        </div>
        <Button type="button" onClick={handleCreate} className="shrink-0 gap-1.5">
          <Plus className="h-4 w-4" aria-hidden="true" />
          Create key
        </Button>
      </CardHeader>
      <CardContent>
        {newKey && (
          <div className="mb-4 rounded-md border border-border bg-muted p-3">
            <p className="text-sm font-medium text-foreground">
              Copy your new key now — you won&apos;t be able to see it again.
            </p>
            <div className="mt-2 flex items-center gap-2">
              <code className="flex-1 truncate rounded border border-border bg-background px-2 py-1.5 text-xs">
                {newKey.fullKey}
              </code>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => copy(newKey.fullKey)}
                className="shrink-0 gap-1.5"
              >
                <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                {copied ? "Copied" : "Copy"}
              </Button>
            </div>
          </div>
        )}

        {keys.length === 0 ? (
          <SettingsEmptyState
            icon={Key}
            title="No API keys yet"
            description="Create a key to start authenticating requests."
          />
        ) : (
          <Table>
            <TableCaption>API keys and their current status</TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Key</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Last used</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {keys.map((key) => (
                <TableRow key={key.id}>
                  <TableCell className="font-medium whitespace-nowrap text-foreground">
                    {key.name}
                  </TableCell>
                  <TableCell className="font-mono text-xs whitespace-nowrap">
                    {key.keyPreview}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {formatShortDate(key.createdAt)}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {key.lastUsedAt ? formatShortDate(key.lastUsedAt) : "Never"}
                  </TableCell>
                  <TableCell>
                    <AdminStatusBadge
                      label={key.status === "active" ? "Active" : "Revoked"}
                      variant={key.status === "active" ? "success" : "muted"}
                    />
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={key.status === "revoked"}
                      onClick={() => handleRevoke(key.id, key.name)}
                    >
                      Revoke
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
