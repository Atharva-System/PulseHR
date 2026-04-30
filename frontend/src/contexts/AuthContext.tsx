import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { User } from "@/types";
import { authApi } from "@/api/services";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const queryClient = useQueryClient();

  // Restore session on mount — verify token is still valid with the server
  useEffect(() => {
    const storedToken = localStorage.getItem("access_token");
    const storedUser = localStorage.getItem("user");
    if (storedToken && storedUser) {
      // Optimistically restore state so protected routes don't flicker
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
      // Then verify with server in background
      authApi
        .me()
        .then(({ data }) => {
          // Update user from server in case profile changed
          localStorage.setItem("user", JSON.stringify(data));
          setUser(data);
        })
        .catch(async () => {
          // Access token invalid — try to refresh before giving up
          const refreshToken = localStorage.getItem("refresh_token");
          if (refreshToken) {
            try {
              const { data } = await authApi.refresh(refreshToken);
              localStorage.setItem("access_token", data.access_token);
              setToken(data.access_token);
            } catch {
              // Refresh also failed — force logout
              localStorage.removeItem("access_token");
              localStorage.removeItem("refresh_token");
              localStorage.removeItem("user");
              setToken(null);
              setUser(null);
            }
          } else {
            localStorage.removeItem("access_token");
            localStorage.removeItem("user");
            setToken(null);
            setUser(null);
          }
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (username: string, password: string) => {
    const { data } = await authApi.login(username, password);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    localStorage.setItem("user", JSON.stringify(data.user));
    setToken(data.access_token);
    setUser(data.user);
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    queryClient.cancelQueries();
    queryClient.clear();
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
