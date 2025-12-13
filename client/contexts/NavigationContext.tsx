"use client";

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import { useRouter, usePathname } from "next/navigation";
import { toast } from "sonner";
import { Chat } from "@/components/layout/Sidebar";

// Dev-only logger
const devLog = (...args: any[]) => {
  if (process.env.NODE_ENV !== "production") {
    console.log(...args);
  }
};

export type TabType = "home" | "chat" | "dashboard" | "tools" | "about";

interface NavigationContextType {
  // Active tab (derived from pathname)
  activeTab: TabType;
  // Navigation
  navigateTo: (tab: TabType) => void;
  // Chat state
  currentChatId: string | undefined;
  setCurrentChatId: (id: string | undefined) => void;
  handleChatIdChange: (chatId: string) => void;
  handleNewChat: () => void;
  handleChatSelect: (chatId: string) => void;
  // Sidebar state
  isSidebarOpen: boolean;
  setIsSidebarOpen: (open: boolean) => void;
  isSidebarCollapsed: boolean;
  setIsSidebarCollapsed: (collapsed: boolean) => void;
  // Agent state
  selectedAgentId: string;
  setSelectedAgentId: (id: string) => void;
  // Streaming state
  isStreaming: boolean;
  setIsStreaming: (streaming: boolean) => void;
  // Chats
  chats: Chat[];
  setChats: (chats: Chat[]) => void;
  fetchChats: (signal?: AbortSignal) => Promise<void>;
  // Edit mode
  isEditMode: boolean;
  setIsEditMode: (mode: boolean) => void;
}

const NavigationContext = createContext<NavigationContextType | null>(null);

export function useNavigation() {
  const context = useContext(NavigationContext);
  if (!context) {
    throw new Error("useNavigation must be used within NavigationProvider");
  }
  return context;
}

// Map pathname to tab
function pathnameToTab(pathname: string): TabType {
  const path = pathname.replace(/^\//, "");
  if (path === "" || path === "home") {
    return "home";
  }
  if (["chat", "dashboard", "tools", "about"].includes(path)) {
    return path as TabType;
  }
  return "home";
}

export function NavigationProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();

  // Derive active tab from pathname
  const activeTab = pathnameToTab(pathname);

  // Chat state
  const [currentChatId, setCurrentChatId] = useState<string | undefined>(
    undefined
  );
  const [chats, setChats] = useState<Chat[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  // Sidebar state
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Agent state
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");

  // Edit mode
  const [isEditMode, setIsEditMode] = useState(false);

  // Load sidebar collapsed state from localStorage
  useEffect(() => {
    const savedCollapsed = localStorage.getItem("sidebarCollapsed");
    if (savedCollapsed !== null) {
      setIsSidebarCollapsed(savedCollapsed === "true");
    }
  }, []);

  // Fetch chats from API
  const fetchChats = useCallback(async (signal?: AbortSignal) => {
    try {
      const response = await fetch("/api/chats", { signal });
      const data = await response.json();

      const chatList: Chat[] = data.map((chat: any) => ({
        id: chat.id,
        title: chat.title,
        lastMessage:
          chat.messages.length > 0
            ? chat.messages[chat.messages.length - 1].content
            : "",
        timestamp: new Date(chat.updated_at),
        preview:
          chat.messages.length > 0
            ? chat.messages[chat.messages.length - 1].content.slice(0, 50) +
              "..."
            : "",
      }));

      setChats(chatList);
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") return;
      console.error("Failed to fetch chat history:", error);
    }
  }, []);

  // Fetch chats on mount
  useEffect(() => {
    const abortController = new AbortController();
    fetchChats(abortController.signal);
    return () => abortController.abort();
  }, [fetchChats]);

  // Navigation
  const navigateTo = useCallback(
    (tab: TabType) => {
      router.push(`/${tab}`);
    },
    [router]
  );

  // Chat handlers
  const handleNewChat = useCallback(() => {
    if (isStreaming) {
      toast.info("Please wait for the current response to complete", {
        description: "You can start a new chat once the response finishes",
      });
      return;
    }
    setCurrentChatId(undefined);
    navigateTo("chat");
    devLog("Starting new chat session");
  }, [isStreaming, navigateTo]);

  const handleChatSelect = useCallback(
    (chatId: string) => {
      if (isStreaming) {
        toast.info("Please wait for the current response to complete", {
          description: "You can switch chats once the response finishes",
        });
        return;
      }
      setCurrentChatId(chatId);
      navigateTo("chat");
      if (window.innerWidth < 1024) {
        setIsSidebarOpen(false);
      }
    },
    [isStreaming, navigateTo]
  );

  const handleChatIdChange = useCallback(
    (chatId: string) => {
      const isNewChat = currentChatId === undefined && chatId !== undefined;
      setCurrentChatId(chatId);
      if (isNewChat) {
        fetchChats();
      }
    },
    [currentChatId, fetchChats]
  );

  // Sidebar collapse handler with localStorage
  const handleSetSidebarCollapsed = useCallback((collapsed: boolean) => {
    setIsSidebarCollapsed(collapsed);
    localStorage.setItem("sidebarCollapsed", collapsed.toString());
  }, []);

  return (
    <NavigationContext.Provider
      value={{
        activeTab,
        navigateTo,
        currentChatId,
        setCurrentChatId,
        handleChatIdChange,
        handleNewChat,
        handleChatSelect,
        isSidebarOpen,
        setIsSidebarOpen,
        isSidebarCollapsed,
        setIsSidebarCollapsed: handleSetSidebarCollapsed,
        selectedAgentId,
        setSelectedAgentId,
        isStreaming,
        setIsStreaming,
        chats,
        setChats,
        fetchChats,
        isEditMode,
        setIsEditMode,
      }}
    >
      {children}
    </NavigationContext.Provider>
  );
}
