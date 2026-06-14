/**
 * Auth context — tracks login state via the JWT in localStorage.
 *
 * Minimal by design: the token itself is the source of truth (attached
 * to requests by api/client.ts). This context exists so components can
 * reactively show/hide UI based on login state and trigger
 * login/logout without prop-drilling.
 */
import { createContext, useContext, useState, type ReactNode } from "react";
import { login as loginRequest, register as registerRequest } from "@/api/endpoints";

interface AuthContextValue {
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    full_name?: string;
    organization_name: string;
  }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const TOKEN_KEY = "gridsuite_token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(
    () => !!localStorage.getItem(TOKEN_KEY)
  );

  async function login(email: string, password: string) {
    const { access_token } = await loginRequest(email, password);
    localStorage.setItem(TOKEN_KEY, access_token);
    setIsAuthenticated(true);
  }

  async function register(payload: {
    email: string;
    password: string;
    full_name?: string;
    organization_name: string;
  }) {
    await registerRequest(payload);
    // Auto-login after registration
    await login(payload.email, payload.password);
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    setIsAuthenticated(false);
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
