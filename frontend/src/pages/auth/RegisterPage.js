import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthLayout } from "@/components/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export default function RegisterPage() {
    const navigate = useNavigate();
    const { register } = useAuth();
    const [form, setForm] = useState({ tenant_name: "", full_name: "", email: "", password: "" });
    const [submitting, setSubmitting] = useState(false);

    const submit = async (e) => {
        e.preventDefault();
        if (form.password.length < 8) {
            toast.error("Password must be at least 8 characters.");
            return;
        }
        setSubmitting(true);
        try {
            await register(form);
            toast.success(`Welcome to ${form.tenant_name}!`);
            navigate("/app/dashboard");
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Registration failed");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <AuthLayout
            title="Create your tenant"
            subtitle="Your account becomes the Tenant Owner."
            footer={
                <span>
                    Already have an account?{" "}
                    <Link to="/login" className="font-medium text-primary" data-testid="register-login-link">
                        Sign in
                    </Link>
                </span>
            }
        >
            <form onSubmit={submit} className="space-y-4" data-testid="register-form">
                <div>
                    <Label htmlFor="tenant_name">Company / tenant name</Label>
                    <Input
                        id="tenant_name"
                        value={form.tenant_name}
                        onChange={(e) => setForm({ ...form, tenant_name: e.target.value })}
                        required
                        data-testid="register-tenant-name-input"
                    />
                </div>
                <div>
                    <Label htmlFor="full_name">Your name</Label>
                    <Input
                        id="full_name"
                        value={form.full_name}
                        onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                        data-testid="register-full-name-input"
                    />
                </div>
                <div>
                    <Label htmlFor="email">Work email</Label>
                    <Input
                        id="email"
                        type="email"
                        value={form.email}
                        onChange={(e) => setForm({ ...form, email: e.target.value })}
                        required
                        data-testid="register-email-input"
                    />
                </div>
                <div>
                    <Label htmlFor="password">Password</Label>
                    <Input
                        id="password"
                        type="password"
                        value={form.password}
                        onChange={(e) => setForm({ ...form, password: e.target.value })}
                        required
                        minLength={8}
                        data-testid="register-password-input"
                    />
                    <p className="mt-1 text-xs text-muted-foreground">At least 8 characters.</p>
                </div>
                <Button type="submit" className="w-full" disabled={submitting} data-testid="register-submit-button">
                    {submitting ? "Creating tenant..." : "Create tenant & sign in"}
                </Button>
            </form>
        </AuthLayout>
    );
}
