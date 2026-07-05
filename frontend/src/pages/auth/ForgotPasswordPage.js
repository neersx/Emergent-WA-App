import { useState } from "react";
import { Link } from "react-router-dom";
import { AuthLayout } from "@/components/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { toast } from "sonner";

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState("");
    const [submitted, setSubmitted] = useState(false);
    const [loading, setLoading] = useState(false);

    const submit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await api.post("/auth/password/forgot", { email });
            setSubmitted(true);
            toast.success("If the email exists, a reset link has been generated.");
        } catch (err) {
            toast.error("Something went wrong.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthLayout
            title="Reset your password"
            subtitle="We'll send a reset token to your email (logged to the server console in dev)."
            footer={
                <span>
                    Remember it?{" "}
                    <Link to="/login" className="font-medium text-primary" data-testid="forgot-back-to-login">
                        Back to sign in
                    </Link>
                </span>
            }
        >
            {submitted ? (
                <div className="text-sm text-muted-foreground" data-testid="forgot-submitted">
                    Check the server console for your reset token. Use it on the{" "}
                    <Link to="/reset-password" className="font-medium text-primary">reset page</Link>.
                </div>
            ) : (
                <form onSubmit={submit} className="space-y-4" data-testid="forgot-form">
                    <div>
                        <Label htmlFor="email">Email</Label>
                        <Input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            data-testid="forgot-email-input"
                        />
                    </div>
                    <Button type="submit" className="w-full" disabled={loading} data-testid="forgot-submit-button">
                        {loading ? "Sending..." : "Send reset link"}
                    </Button>
                </form>
            )}
        </AuthLayout>
    );
}
