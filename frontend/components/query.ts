"use client";

import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useApi<T>(path: string, options?: { interval?: number; enabled?: boolean }) {
  return useQuery({
    queryKey: [path],
    queryFn: ({ signal }) => api<T>(path, { signal }),
    enabled: options?.enabled,
    refetchInterval: options?.interval,
  });
}

export function useWrite<T, V>(operation: (variables: V) => Promise<T>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: operation,
    onSuccess: () => {
      void queryClient.invalidateQueries({ predicate: ({ queryKey }) => queryKey[0] !== "/auth/me" });
    },
  });
}
