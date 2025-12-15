"use client";

import { useState, useEffect } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { Sidebar } from "@/components/layout/Sidebar";
import { EditModePanel } from "@/components/modals/EditModePanel";
import { SpatialNetworkBackground } from "@/components/background/SpatialNetworkBackground";
import { CustomThemeProvider, useThemeContext } from "@/contexts/ThemeContext";
import { AgentsProvider } from "@/contexts/AgentsContext";
import { UserProvider } from "@/contexts/UserContext";
import { NavigationProvider, useNavigation } from "@/contexts/NavigationContext";
import { AppConfigProvider } from "@/contexts/AppConfigContext";

function MainLayoutContent({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);
  const { colors, animatedBackground } = useThemeContext();
  const {
    activeTab,
    currentChatId,
    handleChatSelect,
    handleNewChat,
    isSidebarCollapsed,
    setIsSidebarCollapsed,
    isSidebarOpen,
    setIsSidebarOpen,
    selectedAgentId,
    setSelectedAgentId,
    chats,
    setChats,
    isEditMode,
    setIsEditMode,
  } = useNavigation();

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="h-screen bg-[var(--color-background)] flex flex-col overflow-hidden">
      {/* Top Bar - Fixed position, floats above content */}
      <TopBar
        activeTab={activeTab}
        onEditModeToggle={() => setIsEditMode(!isEditMode)}
      />

      {/* Spacer for fixed header */}
      <div className="flex-shrink-0 h-[var(--header-height)]" />

      {/* Main Layout */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* Sidebar - Only show on Chat tab */}
        {activeTab === "chat" && (
          <>
            {/* Desktop Sidebar */}
            <div className="hidden lg:block flex-shrink-0">
              <Sidebar
                currentChatId={currentChatId}
                onChatSelect={handleChatSelect}
                onNewChat={handleNewChat}
                isCollapsed={isSidebarCollapsed}
                onCollapse={setIsSidebarCollapsed}
                selectedAgentId={selectedAgentId}
                onAgentChange={setSelectedAgentId}
                chats={chats}
                onChatsChange={setChats}
              />
            </div>

            {/* Mobile Sidebar */}
            <Sidebar
              currentChatId={currentChatId}
              onChatSelect={handleChatSelect}
              onNewChat={handleNewChat}
              isMobile
              isOpen={isSidebarOpen}
              onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
              selectedAgentId={selectedAgentId}
              onAgentChange={setSelectedAgentId}
              chats={chats}
              onChatsChange={setChats}
            />
          </>
        )}

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col h-full relative bg-[var(--color-background)] overflow-hidden">
          {/* Background - Only show on home page */}
          {activeTab === "home" && (
            <SpatialNetworkBackground
              particleCount={animatedBackground.particleCount}
              connectionDistance={animatedBackground.connectionDistance}
              primaryColor={colors.animatedBgColor}
              secondaryColor={colors.animatedBgColor}
              particleOpacity={animatedBackground.particleOpacity}
              lineOpacity={animatedBackground.lineOpacity}
              particleSize={animatedBackground.particleSize}
              lineWidth={animatedBackground.lineWidth}
              animationSpeed={animatedBackground.animationSpeed}
            />
          )}

          {/* Page Content */}
          <div className="relative flex-1 flex flex-col min-h-0">
            {children}
          </div>
        </main>
      </div>

      {/* Edit Mode Panel */}
      <EditModePanel isOpen={isEditMode} onClose={() => setIsEditMode(false)} />
    </div>
  );
}

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <CustomThemeProvider>
      <UserProvider>
        <AgentsProvider>
          <AppConfigProvider>
            <NavigationProvider>
              <MainLayoutContent>{children}</MainLayoutContent>
            </NavigationProvider>
          </AppConfigProvider>
        </AgentsProvider>
      </UserProvider>
    </CustomThemeProvider>
  );
}
