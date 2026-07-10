import { useMutation } from "@tanstack/react-query";

import { sendChatMessage } from "@/api/chat";

export function useSendChatMessage() {
  return useMutation({
    mutationFn: sendChatMessage,
  });
}
