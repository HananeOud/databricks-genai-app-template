import { Routes, Route } from 'react-router-dom';
import { CustomThemeProvider } from '@/contexts/ThemeContext';
import { AgentsProvider } from '@/contexts/AgentsContext';
import { UserProvider } from '@/contexts/UserContext';
import { NavigationProvider } from '@/contexts/NavigationContext';
import { AppConfigProvider } from '@/contexts/AppConfigContext';
import { MainLayout } from '@/components/layout/MainLayout';
import { HomePage } from '@/pages/HomePage';
import { ChatPage } from '@/pages/ChatPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { AboutPage } from '@/pages/AboutPage';
import { ToolsPage } from '@/pages/ToolsPage';

function App() {
  return (
    <CustomThemeProvider>
      <UserProvider>
        <AgentsProvider>
          <AppConfigProvider>
            <NavigationProvider>
              <MainLayout>
                <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/home" element={<HomePage />} />
                  <Route path="/chat" element={<ChatPage />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/about" element={<AboutPage />} />
                  <Route path="/tools" element={<ToolsPage />} />
                </Routes>
              </MainLayout>
            </NavigationProvider>
          </AppConfigProvider>
        </AgentsProvider>
      </UserProvider>
    </CustomThemeProvider>
  );
}

export default App;
