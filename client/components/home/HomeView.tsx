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
          <div className="p-6 rounded-2xl bg-[var(--color-bg-secondary)] backdrop-blur-xl border border-[var(--color-border)] shadow-lg space-y-4">
            <p className="text-lg font-medium text-[var(--color-text-primary)]">To configure your project:</p>
            <ol className="list-decimal list-inside space-y-3 text-base text-[var(--color-text-muted)]">
              <li>
                Open{" "}
                <code className="px-2.5 py-1 bg-[var(--color-accent-primary)]/10 backdrop-blur-sm rounded-lg text-sm font-mono text-[var(--color-accent-primary)] border border-[var(--color-accent-primary)]/20">
                  config/app.json
                </code>
              </li>
              <li>
                Update{" "}
                <code className="px-2.5 py-1 bg-[var(--color-accent-primary)]/10 backdrop-blur-sm rounded-lg text-sm font-mono text-[var(--color-accent-primary)] border border-[var(--color-accent-primary)]/20">
                  home.title
                </code>{" "}
                and{" "}
                <code className="px-2.5 py-1 bg-[var(--color-accent-primary)]/10 backdrop-blur-sm rounded-lg text-sm font-mono text-[var(--color-accent-primary)] border border-[var(--color-accent-primary)]/20">
                  home.description
                </code>
              </li>
              <li>
                Configure your{" "}
                <code className="px-2.5 py-1 bg-[var(--color-accent-primary)]/10 backdrop-blur-sm rounded-lg text-sm font-mono text-[var(--color-accent-primary)] border border-[var(--color-accent-primary)]/20">
                  branding
                </code>
                ,{" "}
                <code className="px-2.5 py-1 bg-[var(--color-accent-primary)]/10 backdrop-blur-sm rounded-lg text-sm font-mono text-[var(--color-accent-primary)] border border-[var(--color-accent-primary)]/20">
                  dashboard
                </code>
                , and{" "}
                <code className="px-2.5 py-1 bg-[var(--color-accent-primary)]/10 backdrop-blur-sm rounded-lg text-sm font-mono text-[var(--color-accent-primary)] border border-[var(--color-accent-primary)]/20">
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
