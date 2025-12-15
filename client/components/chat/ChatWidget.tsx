"use client";

import React, { useState, useEffect, useRef } from "react";
import { MessageSquare, X, ExternalLink, Plus, Settings, Check } from "lucide-react";
import { useRouter } from "next/navigation";
import { useAgents } from "@/hooks/useAgents";
import { ChatCore } from "./ChatCore";

interface ChatWidgetProps {
  className?: string;
}

export function ChatWidget({ className = "" }: ChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [chatId, setChatId] = useState<string | undefined>(undefined);
  const [selectedAgentId, setSelectedAgentId] = useState<string | undefined>(
    undefined,
  );
  const [isStreaming, setIsStreaming] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);
  const { agents } = useAgents();
  const router = useRouter();

  // Close settings dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(event.target as Node)) {
        setIsSettingsOpen(false);
      }
    };
    if (isSettingsOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isSettingsOpen]);

  // Set default agent when agents load
  useEffect(() => {
    if (agents.length > 0 && !selectedAgentId) {
      setSelectedAgentId(agents[0].id);
    }
  }, [agents, selectedAgentId]);

  const handleNewConversation = () => {
    setChatId(undefined);
  };

  const handleExpandToFullChat = () => {
    if (chatId) {
      router.push(`/chat?id=${chatId}`);
    } else {
      router.push("/chat");
    }
  };

  const handleChatIdChange = (newChatId: string) => {
    setChatId(newChatId);
  };

  return (
    <div className={`fixed bottom-0 right-6 z-50 ${className}`}>
      {isOpen ? (
        /* Expanded Chat Window */
        <div
          className="w-[720px] h-[850px] bg-[var(--color-bg-secondary)] backdrop-blur-2xl backdrop-saturate-150 rounded-t-3xl shadow-2xl border border-b-0 border-[var(--color-border)] flex flex-col overflow-hidden animate-in slide-in-from-bottom-4 fade-in duration-200"
          style={{
            maxHeight: "calc(100vh - 60px)",
            maxWidth: "calc(100vw - 48px)",
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]/40 bg-[var(--color-bg-secondary)]/60 backdrop-blur-md cursor-pointer hover:bg-[var(--color-accent-primary)]/10 transition-colors" onClick={() => setIsOpen(false)}>
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-[var(--color-accent-primary)]" />
              <span className="font-medium text-sm text-[var(--color-foreground)]">
                Chat
              </span>
            </div>
            <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
              {/* New Conversation Button */}
              <button
                onClick={handleNewConversation}
                disabled={isStreaming}
                className="p-1.5 rounded-lg hover:bg-[var(--color-muted)] transition-colors disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
                title="New conversation"
              >
                <Plus className="h-4 w-4 text-[var(--color-muted-foreground)]" />
              </button>
              {/* Settings Button (only if multiple agents) */}
              {agents.length > 1 && (
                <div className="relative" ref={settingsRef}>
                  <button
                    onClick={() => setIsSettingsOpen(!isSettingsOpen)}
                    className={`p-1.5 rounded-lg hover:bg-[var(--color-muted)] transition-colors cursor-pointer ${isSettingsOpen ? "bg-[var(--color-muted)]" : ""}`}
                    title="Settings"
                  >
                    <Settings className="h-4 w-4 text-[var(--color-muted-foreground)]" />
                  </button>
                  {/* Agent Selection Dropdown */}
                  {isSettingsOpen && (
                    <div className="absolute top-full right-0 mt-1 w-[220px] bg-[var(--color-background)] rounded-xl shadow-xl border border-[var(--color-border)] py-2 z-50">
                      <div className="px-3 py-1.5 text-xs font-medium text-[var(--color-muted-foreground)] uppercase tracking-wide">
                        Select Agent
                      </div>
                      {agents.map((agent) => (
                        <button
                          key={agent.id}
                          onClick={() => {
                            setSelectedAgentId(agent.id);
                            setIsSettingsOpen(false);
                          }}
                          className={`w-full text-left px-3 py-2 hover:bg-[var(--color-muted)] transition-colors flex items-center justify-between gap-2 ${
                            selectedAgentId === agent.id ? "bg-[var(--color-muted)]" : ""
                          }`}
                        >
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-sm text-[var(--color-foreground)] truncate">
                              {agent.display_name}
                            </div>
                          </div>
                          {selectedAgentId === agent.id && (
                            <Check className="h-4 w-4 text-[var(--color-accent-primary)] flex-shrink-0" />
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {/* Expand Button */}
              <button
                onClick={handleExpandToFullChat}
                className="p-1.5 rounded-lg hover:bg-[var(--color-muted)] transition-colors cursor-pointer"
                title="Open full chat"
              >
                <ExternalLink className="h-4 w-4 text-[var(--color-muted-foreground)]" />
              </button>
              {/* Close Button */}
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-lg hover:bg-[var(--color-muted)] transition-colors cursor-pointer"
                title="Close"
              >
                <X className="h-4 w-4 text-[var(--color-muted-foreground)]" />
              </button>
            </div>
          </div>

          {/* Chat Content */}
          <div className="flex-1 flex flex-col min-h-0">
            <ChatCore
              chatId={chatId}
              onChatIdChange={handleChatIdChange}
              selectedAgentId={selectedAgentId}
              onAgentChange={setSelectedAgentId}
              onStreamingChange={setIsStreaming}
              compact
              showAgentSelector={false}
            />
          </div>
        </div>
      ) : (
        /* Collapsed Bar */
        <button
          onClick={() => setIsOpen(true)}
          className="w-[400px] px-4 py-3 bg-[var(--color-bg-secondary)] backdrop-blur-xl backdrop-saturate-150 rounded-t-2xl shadow-xl border border-b-0 border-[var(--color-border)] flex items-center gap-3 hover:border-[var(--color-accent-primary)]/50 hover:shadow-2xl transition-all duration-300 group cursor-pointer"
          style={{ maxWidth: "calc(100vw - 48px)" }}
        >
          <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-[var(--color-accent-primary)] to-[var(--color-accent-primary)]/80 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform shadow-lg">
            <MessageSquare className="h-5 w-5 text-white" />
          </div>
          <div className="flex-1 text-left">
            <span className="text-sm font-medium text-[var(--color-foreground)]">
              Ask a question...
            </span>
          </div>
        </button>
      )}
    </div>
  );
}
