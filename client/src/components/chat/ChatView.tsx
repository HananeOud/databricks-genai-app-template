
import React from "react";
import { ChatCore } from "./ChatCore";

interface ChatViewProps {
  chatId?: string;
  onChatIdChange?: (chatId: string) => void;
  selectedAgentId?: string;
  onAgentChange?: (agentId: string) => void;
  initialMessage?: string;
  onStreamingChange?: (isStreaming: boolean) => void;
}

export function ChatView({
  chatId,
  onChatIdChange,
  selectedAgentId,
  onAgentChange,
  initialMessage,
  onStreamingChange,
}: ChatViewProps) {
  return (
    <ChatCore
      chatId={chatId}
      onChatIdChange={onChatIdChange}
      selectedAgentId={selectedAgentId}
      onAgentChange={onAgentChange}
      initialMessage={initialMessage}
      onStreamingChange={onStreamingChange}
      compact={false}
      showAgentSelector={true}
    />
  );
}
