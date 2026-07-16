"use client";

import { ShieldCheck } from "lucide-react";
import { useState, type ChangeEvent } from "react";

import { formatRelativeTime } from "@/components/ActivityList";
import { Button } from "@/components/ui/button";
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
import securityData from "@/lib/mock-data/admin-security.json";
import sessionsData from "@/lib/mock-data/admin-sessions.json";
import { toast } from "@/lib/toast";

import { AdminStatusBadge } from "./AdminStatusBadge";
import { openConfirmDialog } from "./ConfirmDialog";
import { SettingsEmptyState } from "./SettingsEmptyState";
import { SettingsPageSkeleton } from "./SettingsPageSkeleton";

interface Session {
  id: string;
  device: string;
  location: string;
  lastActiveAt: string;
  isCurrent: boolean;
}

interface SecurityData {
  twoFactorEnabled: boolean;
  lastPasswordChangeAt: string;
}

const defaultSecurity = securityData as SecurityData;
const seedSessions = sessionsData as Session[];

export function SecuritySettings() {
  const isLoading = useSimulatedLoad();
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(
    defaultSecurity.twoFactorEnabled
  );
  const [sessions, setSessions] = useState<Session[]>(seedSessions);

  if (isLoading) {
    return <SettingsPageSkeleton />;
  }

  const handleToggleTwoFactor = (event: ChangeEvent<HTMLInputElement>) => {
    setTwoFactorEnabled(event.target.checked);
  };

  const handleSignOut = (id: string, device: string) => {
    openConfirmDialog({
      title: "Sign out this session?",
      description: `"${device}" will be signed out immediately.`,
      confirmLabel: "Sign out",
      variant: "destructive",
      onConfirm: () => {
        setSessions((prev) => prev.filter((session) => session.id !== id));
      },
    });
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle level="h2">Password</CardTitle>
          <CardDescription>
            Last changed {formatRelativeTime(defaultSecurity.lastPasswordChangeAt)}.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              toast("Password changes aren't available in this preview.")
            }
          >
            Change password
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle level="h2">Two-factor authentication</CardTitle>
          <CardDescription>
            Require a verification code in addition to your password.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between rounded-md border border-border p-3">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent text-accent-foreground">
                <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">
                  {twoFactorEnabled ? "Enabled" : "Disabled"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {twoFactorEnabled
                    ? "Your account is protected with 2FA."
                    : "Turn on 2FA for extra account security."}
                </p>
              </div>
            </div>
            <Switch
              checked={twoFactorEnabled}
              onChange={handleToggleTwoFactor}
              aria-label="Two-factor authentication"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle level="h2">Active sessions</CardTitle>
          <CardDescription>
            Devices currently signed in to your account.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sessions.length === 0 ? (
            <SettingsEmptyState
              title="No active sessions"
              description="Sign in again to start a new session."
            />
          ) : (
            <Table>
              <TableCaption>
                Active sessions signed in to your account
              </TableCaption>
              <TableHeader>
                <TableRow>
                  <TableHead>Device</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Last active</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessions.map((session) => (
                  <TableRow key={session.id}>
                    <TableCell className="whitespace-nowrap">
                      <span className="font-medium text-foreground">
                        {session.device}
                      </span>
                      {session.isCurrent && (
                        <span className="ml-2 inline-block align-middle">
                          <AdminStatusBadge label="This device" variant="info" />
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-muted-foreground">
                      {session.location}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-muted-foreground">
                      {formatRelativeTime(session.lastActiveAt)}
                    </TableCell>
                    <TableCell className="text-right">
                      {!session.isCurrent && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSignOut(session.id, session.device)}
                        >
                          Sign out
                        </Button>
                      )}
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
