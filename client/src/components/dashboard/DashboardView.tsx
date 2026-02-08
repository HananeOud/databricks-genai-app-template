import React, { useEffect, useState } from "react";
import { Sparkles, ExternalLink } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { getAppConfig, type DashboardConfig } from "@/lib/config";
import { useUserInfo } from "@/hooks/useUserInfo";

export function DashboardView() {
  const navigate = useNavigate();
  const { userInfo } = useUserInfo();
  const [dashboard, setDashboard] = useState<DashboardConfig>({
    title: "Dashboard",
    subtitle: "Loading...",
    dashboardId: "",
    showPadding: true,
  });

  useEffect(() => {
    getAppConfig().then((config) => setDashboard(config.dashboard));
  }, []);

  const { title, subtitle, dashboardId, showPadding } = dashboard;

  // Build the embed URL from dashboardId and workspace URL
  const iframeUrl = dashboardId && userInfo?.workspace_url
    ? `${userInfo.workspace_url}/embed/dashboardsv3/${dashboardId}`
    : "";

  // Case 1: Dashboard iframe is provided
  if (iframeUrl) {
    return (
      <div className="h-full flex flex-col overflow-hidden">
        {/* Header with title, subtitle, and buttons */}
        <div className="flex-shrink-0 px-6 pt-6 pb-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-[var(--color-text-heading)] mb-2">
                {title}
              </h1>
              <p className="text-base text-[var(--color-text-muted)]">
                {subtitle}
              </p>
            </div>

            <div className="flex items-center gap-3">
              {/* Open in new tab fallback */}
              <a
                href={iframeUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[var(--color-bg-secondary)] hover:bg-[var(--color-bg-tertiary)] border border-[var(--color-border)] transition-all duration-200 group shadow-sm hover:shadow-md text-[var(--color-text-primary)] text-sm font-medium"
                title="Open dashboard in a new tab"
              >
                <ExternalLink className="h-4 w-4 opacity-70 group-hover:opacity-100 transition-opacity" />
                Open in new tab
              </a>

              {/* Ask Agent Button */}
              <button
                onClick={() => navigate("/chat")}
                className="flex-shrink-0 p-3 rounded-xl bg-[#0C1C3E] hover:bg-[#152a52] transition-all duration-200 group shadow-sm hover:shadow-md"
                aria-label="Ask the AI agent"
              >
                <Sparkles className="h-5 w-5 text-white transition-transform group-hover:rotate-12" />
              </button>
            </div>
          </div>
        </div>

        {/* Dashboard iframe */}
        <div
          className={`flex-1 overflow-hidden ${showPadding ? "px-6 pb-6" : ""}`}
        >
          <iframe
            src={iframeUrl}
            className="w-full h-full border-0 rounded-lg"
            title={title}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-storage-access-by-user-activation"
          />
        </div>
      </div>
    );
  }

  // Case 2: No dashboard configured - show placeholder
  return (
    <div className="h-full flex items-center px-12">
      <div className="max-w-4xl space-y-8">
        {/* Large placeholder title */}
        <h1 className="text-7xl font-bold text-[var(--color-text-heading)] leading-tight">
          This is where your<br></br> cool AI/BI dashboard will be embedded
        </h1>

        {/* Instructions */}
        <div className="p-6 rounded-2xl bg-[var(--color-bg-secondary)] backdrop-blur-xl border border-[var(--color-border)] shadow-lg space-y-4">
          <p className="text-lg font-medium text-[var(--color-text-primary)]">To configure your dashboard:</p>
          <ol className="list-decimal list-inside space-y-3 text-base text-[var(--color-text-muted)]">
            <li>
              Open{" "}
              <code className="px-2.5 py-1 bg-[var(--color-accent-primary)]/10 backdrop-blur-sm rounded-lg text-sm font-mono text-[var(--color-accent-primary)] border border-[var(--color-accent-primary)]/20">
                config/app.json
              </code>
            </li>
            <li>
              Set the{" "}
              <code className="px-2.5 py-1 bg-[var(--color-accent-primary)]/10 backdrop-blur-sm rounded-lg text-sm font-mono text-[var(--color-accent-primary)] border border-[var(--color-accent-primary)]/20">
                dashboard.dashboardId
              </code>{" "}
              to your Databricks dashboard ID
            </li>
            <li>
              Customize the{" "}
              <code className="px-2.5 py-1 bg-[var(--color-accent-primary)]/10 backdrop-blur-sm rounded-lg text-sm font-mono text-[var(--color-accent-primary)] border border-[var(--color-accent-primary)]/20">
                dashboard.title
              </code>{" "}
              and{" "}
              <code className="px-2.5 py-1 bg-[var(--color-accent-primary)]/10 backdrop-blur-sm rounded-lg text-sm font-mono text-[var(--color-accent-primary)] border border-[var(--color-accent-primary)]/20">
                dashboard.subtitle
              </code>{" "}
              as needed
            </li>
            <li>Restart the development server to see your changes</li>
          </ol>
        </div>

        {/* Ask Agent Button */}
        <div className="flex items-center gap-4 pt-4">
          <span className="text-[var(--color-text-muted)]">
            In the meantime, try asking your AI agent:
          </span>
          <button
            onClick={() => navigate("/chat")}
            className="p-3 rounded-xl bg-[#0C1C3E] hover:bg-[#152a52] transition-all duration-200 group shadow-sm hover:shadow-md"
            aria-label="Ask the AI agent"
          >
            <Sparkles className="h-5 w-5 text-white transition-transform group-hover:rotate-12" />
          </button>
        </div>
      </div>
    </div>
  );
}
