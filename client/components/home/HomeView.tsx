"use client";

import React from "react";
import { useAppConfig } from "@/contexts/AppConfigContext";
import { ChatWidget } from "@/components/chat/ChatWidget";

export function HomeView() {
  const { config, isLoading } = useAppConfig();

  if (isLoading || !config) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-[var(--color-text-muted)]">Loading...</div>
      </div>
    );
  }

  const { home } = config;

  return (
    <>
      <div className="h-full flex items-center px-12">
        <div className="max-w-4xl space-y-8">
          {/* Large title */}
          <h1 className="text-7xl font-bold text-[var(--color-text-heading)] leading-tight">
            {home.title}
          </h1>

          {/* Description */}
          <p className="text-xl text-[var(--color-text-muted)] leading-relaxed max-w-2xl">
            {home.description}
          </p>

          {/* Config instructions */}
          <div className="space-y-4 text-[var(--color-text-muted)]">
            <p className="text-lg">To configure your project:</p>
            <ol className="list-decimal list-inside space-y-2 text-base ml-4">
              <li>
                Open{" "}
                <code className="px-2 py-1 bg-[var(--color-muted)]/30 rounded text-sm font-mono text-[var(--color-accent-primary)]">
                  config/app.json
                </code>
              </li>
              <li>
                Update{" "}
                <code className="px-2 py-1 bg-[var(--color-muted)]/30 rounded text-sm font-mono text-[var(--color-accent-primary)]">
                  home.title
                </code>{" "}
                and{" "}
                <code className="px-2 py-1 bg-[var(--color-muted)]/30 rounded text-sm font-mono text-[var(--color-accent-primary)]">
                  home.description
                </code>
              </li>
              <li>
                Configure your{" "}
                <code className="px-2 py-1 bg-[var(--color-muted)]/30 rounded text-sm font-mono text-[var(--color-accent-primary)]">
                  branding
                </code>
                ,{" "}
                <code className="px-2 py-1 bg-[var(--color-muted)]/30 rounded text-sm font-mono text-[var(--color-accent-primary)]">
                  dashboard
                </code>
                , and{" "}
                <code className="px-2 py-1 bg-[var(--color-muted)]/30 rounded text-sm font-mono text-[var(--color-accent-primary)]">
                  about
                </code>{" "}
                sections
              </li>
              <li>Restart the development server to see your changes</li>
            </ol>
          </div>
        </div>
      </div>

      {/* Chat Widget */}
      <ChatWidget />
    </>
  );
}
