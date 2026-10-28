import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, authApi } from "../services/api";
import type { User } from "../types";

export const ME_KEY = ["auth", "me"] as const;

/** Utilisateur connecté ; null si pas de session (401). */
export function useMe() {
  return useQuery<User | null>({
    queryKey: ME_KEY,
    queryFn: async () => {
      try {
        return await authApi.me();
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    staleTime: 5 * 60_000,
  });
}

export function useAuthConfig() {
  return useQuery({ queryKey: ["auth", "config"], queryFn: authApi.config, staleTime: Infinity });
}

/** Connexion / inscription : enregistre l'utilisateur renvoyé comme utilisateur courant. */
export function useSignIn<T>(fn: (input: T) => Promise<User>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (user) => queryClient.setQueryData(ME_KEY, user),
  });
}

/** Déconnexion (ou suppression du compte) : vide tout le cache, données de marché comprises. */
export function useSignOut(fn: () => Promise<void> = authApi.logout) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      queryClient.clear();
      queryClient.setQueryData(ME_KEY, null);
    },
  });
}
