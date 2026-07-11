import {
  MutationCache,
  QueryCache,
  QueryClient,
  isServer,
} from "@tanstack/react-query";

import { normalizeError } from "@/lib/api/errors";
import { logger } from "@/lib/logger";

function makeQueryClient() {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (error, query) => {
        logger.error(
          `Query failed: ${JSON.stringify(query.queryKey)}`,
          normalizeError(error)
        );
      },
    }),
    mutationCache: new MutationCache({
      onError: (error, _variables, _context, mutation) => {
        logger.error(
          `Mutation failed: ${JSON.stringify(mutation.options.mutationKey ?? "unknown")}`,
          normalizeError(error)
        );
      },
    }),
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

export function getQueryClient() {
  if (isServer) {
    return makeQueryClient();
  }

  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}
