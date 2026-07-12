import {
  ServerCard,
  type ServerStatusValue,
} from "@/components/Cards/ServerCard";
import serverStatusData from "@/lib/mock-data/server-status.json";

interface ServerEntry {
  id: string;
  name: string;
  status: ServerStatusValue;
  uptime: string;
}

const servers = serverStatusData as ServerEntry[];

export function ServerStatus() {
  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold text-foreground">
        Server Status
      </h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {servers.map((server) => (
          <ServerCard
            key={server.id}
            name={server.name}
            status={server.status}
            uptime={server.uptime}
          />
        ))}
      </div>
    </div>
  );
}
