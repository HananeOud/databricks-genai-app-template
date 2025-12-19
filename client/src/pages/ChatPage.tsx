import { ChatView } from "@/components/chat/ChatView";
import { useNavigation } from "@/contexts/NavigationContext";

export function ChatPage() {
  const {
    currentChatId,
    handleChatIdChange,
    selectedAgentId,
    setSelectedAgentId,
    setIsStreaming,
  } = useNavigation();

  return (
    <ChatView
      chatId={currentChatId}
      onChatIdChange={handleChatIdChange}
      selectedAgentId={selectedAgentId}
      onAgentChange={setSelectedAgentId}
      onStreamingChange={setIsStreaming}
    />
  );
}
