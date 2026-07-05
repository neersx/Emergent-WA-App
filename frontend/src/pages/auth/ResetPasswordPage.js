import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AuthLayout } from "@/components/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { toast } from "sonner";

export default function ResetPasswordPage() {
    const navigate = useNavigate();
    const [sp] = useSearchParams();
    const [token, setToken] = useState(sp.get("token") || "");
    const [newPassword, setNewPassword] = useState("");
    const [loading, setLoading] = useState(false);

    const submit = async (e) => {
        e.preventDefault();
        if (newPassword.length < 8) {
            toast.error("Password must be at least 8 characters.");
            return;
        }
        setLoading(true);
        try {
            await api.post("/auth/password/reset", { token, new_password: newPassword });
            toast.success("Password reset. Please sign in.");
            navigate("/login");
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Invalid or expired token");
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthLayout
            title="Set a new password"
            subtitle="Paste the reset token from the server console."
            footer={
                <span>
                    <Link to="/login" className="font-medium text-primary">
                        Back to sign in
                    </Link>
                </span>
            }
        >
            <form onSubmit={submit} className="space-y-4" data-testid="reset-form">
                <div>
                    <Label htmlFor="token">Reset token</Label>
                    <Input
                        id="token"
                        value={token}
                        onChange={(e) => setToken(e.target.value)}
                        required
                        data-testid="reset-token-input"
                    />
                </div>
                <div>
                    <Label htmlFor="new_password">New password</Label>
                    <Input
                        id="new_password"
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        required
                        minLength={8}
                        data-testid="reset-password-input"
                    />
                </div>
                <Button type="submit" className="w-full" disabled={loading} data-testid="reset-submit-button">
                    {loading ? "Updating..." : "Update password"}
                </Button>
            </form>
        </AuthLayout>
    );
}
