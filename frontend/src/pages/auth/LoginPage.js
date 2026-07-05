import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { AuthLayout } from "@/components/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";

export default function LoginPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const { login } = useAuth();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [mfaCode, setMfaCode] = useState("");
    const [needsMfa, setNeedsMfa] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    const submit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            const res = await login(email, password, needsMfa ? mfaCode : undefined);
            if (res.mfa_required && !needsMfa) {
                setNeedsMfa(true);
                toast.info("Enter the 6-digit code from your authenticator app.");
            } else if (res.mfa_setup_required) {
                navigate("/app/security?setup=1");
            } else {
                const from = location.state?.from?.pathname || "/app/dashboard";
                navigate(from);
            }
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Invalid credentials");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <AuthLayout
            title={needsMfa ? "Two-factor verification" : "Welcome back"}
            subtitle={needsMfa ? "Enter the 6-digit code from your authenticator app." : "Sign in to your WABA Console account."}
            footer={
                <span>
                    Don&apos;t have an account?{" "}
                    <Link to="/register" className="font-medium text-primary" data-testid="login-register-link">
                        Get started
                    </Link>
                </span>
            }
        >
            <form onSubmit={submit} className="space-y-4" data-testid="login-form">
                {!needsMfa && (
                    <>
                        <div>
                            <Label htmlFor="email">Email</Label>
                            <Input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                autoComplete="email"
                                required
                                data-testid="login-email-input"
                            />
                        </div>
                        <div>
                            <div className="flex items-center justify-between">
                                <Label htmlFor="password">Password</Label>
                                <Link
                                    to="/forgot-password"
                                    className="text-xs text-primary"
                                    data-testid="login-forgot-link"
                                >
                                    Forgot?
                                </Link>
                            </div>
                            <Input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                autoComplete="current-password"
                                required
                                data-testid="login-password-input"
                            />
                        </div>
                    </>
                )}
                {needsMfa && (
                    <div>
                        <Label>Authenticator code</Label>
                        <InputOTP
                            maxLength={6}
                            value={mfaCode}
                            onChange={setMfaCode}
                            data-testid="mfa-otp-input"
                        >
                            <InputOTPGroup>
                                {[0, 1, 2, 3, 4, 5].map((i) => (
                                    <InputOTPSlot key={i} index={i} />
                                ))}
                            </InputOTPGroup>
                        </InputOTP>
                    </div>
                )}
                <Button type="submit" className="w-full" disabled={submitting} data-testid="login-submit-button">
                    {submitting ? "Signing in..." : needsMfa ? "Verify code" : "Sign in"}
                </Button>
            </form>
        </AuthLayout>
    );
}
