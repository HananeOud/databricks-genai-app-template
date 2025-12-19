import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";

interface UserContextType {
  user: string | null;
  workspaceUrl: string | null;
  lakebaseConfigured: boolean;
  lakebaseProjectId: string | null;
  lakebaseError: string | null;
  loading: boolean;
  error: Error | null;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function useUserContext() {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error("useUserContext must be used within a UserProvider");
  }
  return context;
}

interface UserProviderProps {
  children: ReactNode;
}

export function UserProvider({ children }: UserProviderProps) {
  const [user, setUser] = useState<string | null>(null);
  const [workspaceUrl, setWorkspaceUrl] = useState<string | null>(null);
  const [lakebaseConfigured, setLakebaseConfigured] = useState(false);
  const [lakebaseProjectId, setLakebaseProjectId] = useState<string | null>(null);
  const [lakebaseError, setLakebaseError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    fetch("/api/me")
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Failed to load user info: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        if (data.error) {
          throw new Error(data.error);
        }
        setUser(data.user);
        setWorkspaceUrl(data.workspace_url);
        setLakebaseConfigured(data.lakebase_configured || false);
        setLakebaseProjectId(data.lakebase_project_id || null);
        setLakebaseError(data.lakebase_error || null);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load user info:", err);
        setError(err);
        setLoading(false);
      });
  }, []);

  return (
    <UserContext.Provider
      value={{
        user,
        workspaceUrl,
        lakebaseConfigured,
        lakebaseProjectId,
        lakebaseError,
        loading,
        error,
      }}
    >
      {children}
    </UserContext.Provider>
  );
}
