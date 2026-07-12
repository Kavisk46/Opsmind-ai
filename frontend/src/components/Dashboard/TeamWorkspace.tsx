import { Avatar } from "@/components/ui/avatar";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import teamMembersData from "@/lib/mock-data/team-members.json";
import { cn } from "@/lib/utils";

type MemberStatus = "online" | "away" | "offline";

interface TeamMember {
  id: string;
  name: string;
  role: string;
  status: MemberStatus;
}

const members = teamMembersData as TeamMember[];

const STATUS_LABEL: Record<MemberStatus, string> = {
  online: "Online",
  away: "Away",
  offline: "Offline",
};

const STATUS_DOT_CLASS: Record<MemberStatus, string> = {
  online: "bg-success",
  away: "bg-warning",
  offline: "bg-muted-foreground",
};

export function TeamWorkspace() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Team Workspace</CardTitle>
        <CardDescription>Who&apos;s active right now</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {members.map((member) => (
            <li key={member.id} className="flex items-center gap-3">
              <span className="relative shrink-0">
                <Avatar name={member.name} size={36} />
                <span
                  className={cn(
                    "absolute right-0 bottom-0 h-2.5 w-2.5 rounded-full ring-2 ring-card",
                    STATUS_DOT_CLASS[member.status]
                  )}
                  aria-hidden="true"
                />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">
                  {member.name}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {member.role}
                </p>
              </div>
              <span className="shrink-0 text-xs text-muted-foreground">
                {STATUS_LABEL[member.status]}
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
