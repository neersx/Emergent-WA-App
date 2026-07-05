import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchMe = async () => {
        try {
            const r = await api.get("/auth/me");
            setUser(r.data);
        } catch {
            setUser(null);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMe();
    }, []);

    const login = async (email, password, mfa_code) => {
        const r = await api.post("/auth/login", { email, password, mfa_code });
        if (!r.data.mfa_required || r.data.user.mfa_enabled === false) {
            await fetchMe();
        }
        return r.data;
    };

    const register = async (payload) => {
        const r = await api.post("/auth/register", payload);
        await fetchMe();
        return r.data;
    };

    const logout = async () => {
        try {
            await api.post("/auth/logout");
        } catch (_) {}
        setUser(null);
    };

    const refreshMe = fetchMe;

    const value = useMemo(
        () => ({ user, loading, login, register, logout, refreshMe, setUser }),
        [user, loading],
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
    return ctx;
}
