import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";

import HomePage from "@/pages/marketing/HomePage";
import PricingPage from "@/pages/marketing/PricingPage";
import FeaturesPage from "@/pages/marketing/FeaturesPage";
import ContactPage from "@/pages/marketing/ContactPage";

import LoginPage from "@/pages/auth/LoginPage";
import RegisterPage from "@/pages/auth/RegisterPage";
import ForgotPasswordPage from "@/pages/auth/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/auth/ResetPasswordPage";

import DashboardPage from "@/pages/admin/DashboardPage";
import ConnectPage from "@/pages/admin/ConnectPage";
import WabasPage from "@/pages/admin/WabasPage";
import TemplatesPage from "@/pages/admin/TemplatesPage";
import SendPage from "@/pages/admin/SendPage";
import MessagesPage from "@/pages/admin/MessagesPage";
import InboxPage from "@/pages/admin/InboxPage";
import AnalyticsPage from "@/pages/admin/AnalyticsPage";
import UsagePage from "@/pages/admin/UsagePage";
import SecurityPage from "@/pages/admin/SecurityPage";
import SettingsPage from "@/pages/admin/SettingsPage";
import PlatformPage from "@/pages/admin/PlatformPage";

function App() {
    return (
        <div className="App">
            <AuthProvider>
                <BrowserRouter>
                    <Routes>
                        {/* Marketing */}
                        <Route path="/" element={<HomePage />} />
                        <Route path="/pricing" element={<PricingPage />} />
                        <Route path="/features" element={<FeaturesPage />} />
                        <Route path="/contact" element={<ContactPage />} />

                        {/* Auth */}
                        <Route path="/login" element={<LoginPage />} />
                        <Route path="/register" element={<RegisterPage />} />
                        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                        <Route path="/reset-password" element={<ResetPasswordPage />} />

                        {/* Admin (protected) */}
                        <Route element={<ProtectedRoute />}>
                            <Route path="/app" element={<Navigate to="/app/dashboard" replace />} />
                            <Route path="/app/dashboard" element={<DashboardPage />} />
                            <Route path="/app/connect" element={<ConnectPage />} />
                            <Route path="/app/wabas" element={<WabasPage />} />
                            <Route path="/app/templates" element={<TemplatesPage />} />
                            <Route path="/app/send" element={<SendPage />} />
                            <Route path="/app/messages" element={<MessagesPage />} />
                            <Route path="/app/inbox" element={<InboxPage />} />
                            <Route path="/app/analytics" element={<AnalyticsPage />} />
                            <Route path="/app/usage" element={<UsagePage />} />
                            <Route path="/app/security" element={<SecurityPage />} />
                            <Route path="/app/settings" element={<SettingsPage />} />
                            <Route path="/app/platform" element={<PlatformPage />} />
                        </Route>

                        {/* Fallback */}
                        <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                    <Toaster position="top-right" richColors closeButton />
                </BrowserRouter>
            </AuthProvider>
        </div>
    );
}

export default App;
