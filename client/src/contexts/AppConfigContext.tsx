import React, { createContext, useContext, useState, useEffect } from 'react';
import { getAppConfig, type AppConfig } from "@/lib/config";

interface AppConfigContextType {
  config: AppConfig | null;
  isLoading: boolean;
  error: string | null;
}

const AppConfigContext = createContext<AppConfigContextType>({
  config: null,
  isLoading: true,
  error: null,
});

export function useAppConfig() {
  return useContext(AppConfigContext);
}

export function AppConfigProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAppConfig()
      .then((cfg) => {
        setConfig(cfg);
        setIsLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setIsLoading(false);
      });
  }, []);

  return (
    <AppConfigContext.Provider value={{ config, isLoading, error }}>
      {children}
    </AppConfigContext.Provider>
  );
}
