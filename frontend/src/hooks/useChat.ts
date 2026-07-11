import { useMutation } from "@tanstack/react-query";
import { useQuery } from "@tanstack/react-query";

import {
  createChatSession,
  deleteChatSession,
  getChatSession,
  listChatSessions,
  sendChatMessage,
  updateChatSession,
} from "@/api/chat";
import { queryClient } from "@/services/queryClient";

export function useSendChatMessage() {
  return useMutation({
    mutationFn: sendChatMessage,
  });
}

export function useChatSessions() {
  return useQuery({
    queryKey: ["chat-sessions"],
    queryFn: listChatSessions,
  });
}

export function useChatSession(sessionId: string | null) {
  return useQuery({
    queryKey: ["chat-session", sessionId],
    queryFn: () => getChatSession(sessionId as string),
    enabled: Boolean(sessionId),
  });
}

export function useCreateChatSession() {
  return useMutation({
    mutationFn: createChatSession,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["chat-sessions"] }),
  });
}

export function useUpdateChatSession() {
  return useMutation({
    mutationFn: updateChatSession,
    onSuccess: (session) => {
      void queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });
      void queryClient.invalidateQueries({ queryKey: ["chat-session", session.session_id] });
    },
  });
}

export function useDeleteChatSession() {
  return useMutation({
    mutationFn: deleteChatSession,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["chat-sessions"] }),
  });
}
