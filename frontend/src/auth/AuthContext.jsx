import { createContext, useContext, useEffect, useState } from "react";
import client, { setAuthToken } from "../api/client";

const AuthContext = createContext(null);

const TOKEN_STORAGE_KEY = "tdp_access_token";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY));
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setAuthToken(token);

    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    client
      .get("/api/auth/me")
      .then((response) => setUser(response.data))
      .catch(() => {
        // Token is invalid/expired - clear it rather than leave the app
        // stuck thinking it's authenticated.
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        setToken(null);
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, [token]);

  function applyToken(newToken) {
    localStorage.setItem(TOKEN_STORAGE_KEY, newToken);
    setToken(newToken);
  }

  async function login(email, password) {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const response = await client.post("/api/auth/login", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    applyToken(response.data.access_token);
  }

  async function register(email, password, organizationName) {
    const response = await client.post("/api/auth/register", {
      email,
      password,
      organization_name: organizationName || undefined,
    });
    applyToken(response.data.access_token);
  }

  function logout() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{ token, user, isAuthenticated: Boolean(token), isLoading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
