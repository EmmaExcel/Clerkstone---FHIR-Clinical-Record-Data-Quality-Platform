import { QueryClient } from "@tanstack/react-query";


export const defaultQueryClientOptions = {
  queries: {
    retry: 1,
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  },
  mutations: {
    retry: 0,
  },
} as const;

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: defaultQueryClientOptions,
  });
}
