import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { ShieldCheck, ShieldAlert, KeyRound } from "lucide-react";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

export default function SecurityPage() {
    const { user, refreshMe } = useAuth();
    const [setup, setSetup] = useState(null); // { secret, otpauth_uri, qr_data_url }
    const [code, setCode] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [disablePwd, setDisablePwd] = useState("");
    const [disableCode, setDisableCode] = useState("");

    useEffect(() => {
        if (user?.mfa_required && !user?.mfa_enabled && !setup) {
            startSetup();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [user]);

    const startSetup = async () => {
        try {
            const r = await api.post("/auth/mfa/setup");
            setSetup(r.data);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Failed to start MFA setup");
        }
    };

    const verifySetup = async () => {
        if (code.length !== 6) {
            toast.error("Enter the 6-digit code from your app.");
            return;
        }
        setSubmitting(true);
        try {
            await api.post("/auth/mfa/verify", { code });
            toast.success("MFA enabled!");
            setSetup(null);
            setCode("");
            await refreshMe();
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Invalid code");
        } finally {
            setSubmitting(false);
        }
    };

    const disableMfa = async () => {
        try {
            await api.post("/auth/mfa/disable", { password: disablePwd, code: disableCode });
            toast.success("MFA disabled");
            setDisablePwd("");
            setDisableCode("");
            await refreshMe();
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Disable failed");
        }
    };

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Admin / Security</span>}
                title="Security & MFA"
                description="Protect your account with TOTP-based two-factor authentication."
            />
            <div className="grid gap-6 lg:grid-cols-2">
                <div className="rounded-xl border bg-card p-6">
                    <div className="flex items-start gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                            <ShieldCheck className="h-5 w-5" />
                        </div>
                        <div className="flex-1">
                            <div className="flex items-center gap-2 text-base font-semibold">
                                Two-factor authentication
                                {user?.mfa_enabled ? (
                                    <span className="inline-flex items-center rounded-full border bg-[hsl(152_55%_93%)] px-2 py-0.5 text-xs font-medium text-[hsl(152_55%_26%)]" data-testid="mfa-status-on">Enabled</span>
                                ) : (
                                    <span className="inline-flex items-center rounded-full border bg-[hsl(0_90%_96%)] px-2 py-0.5 text-xs font-medium text-[hsl(0_70%_40%)]" data-testid="mfa-status-off">Disabled</span>
                                )}
                            </div>
                            <p className="mt-1 text-sm text-muted-foreground">
                                {user?.mfa_required && !user?.mfa_enabled
                                    ? "MFA is required for your role. Please complete setup below."
                                    : "Use any TOTP app (1Password, Authy, Google Authenticator)."}
                            </p>
                        </div>
                    </div>

                    {!user?.mfa_enabled && !setup && (
                        <Button className="mt-6" onClick={startSetup} data-testid="mfa-setup-start">
                            <KeyRound className="mr-2 h-4 w-4" /> Enable MFA
                        </Button>
                    )}

                    {setup && (
                        <div className="mt-6 space-y-4" data-testid="mfa-setup-panel">
                            <div className="rounded-lg border bg-background p-4">
                                <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-start">
                                    <img src={setup.qr_data_url} alt="MFA QR code" className="h-40 w-40 rounded-md border bg-white p-2" data-testid="mfa-qr-image" />
                                    <div className="text-sm">
                                        <div className="text-muted-foreground">Scan with your authenticator app, or paste this secret manually:</div>
                                        <div className="mt-2 break-all rounded bg-secondary/40 p-2 font-mono text-xs" data-testid="mfa-secret">{setup.secret}</div>
                                    </div>
                                </div>
                            </div>
                            <div>
                                <Label>Enter the 6-digit code</Label>
                                <InputOTP maxLength={6} value={code} onChange={setCode} data-testid="mfa-otp-input">
                                    <InputOTPGroup>
                                        {[0, 1, 2, 3, 4, 5].map((i) => (
                                            <InputOTPSlot key={i} index={i} />
                                        ))}
                                    </InputOTPGroup>
                                </InputOTP>
                            </div>
                            <Button onClick={verifySetup} disabled={submitting} data-testid="mfa-verify-button">
                                {submitting ? "Verifying..." : "Verify & enable"}
                            </Button>
                        </div>
                    )}

                    {user?.mfa_enabled && (
                        <div className="mt-6">
                            <AlertDialog>
                                <AlertDialogTrigger asChild>
                                    <Button variant="outline" data-testid="mfa-disable-trigger">
                                        <ShieldAlert className="mr-2 h-4 w-4" /> Disable MFA
                                    </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                    <AlertDialogHeader>
                                        <AlertDialogTitle>Disable two-factor authentication?</AlertDialogTitle>
                                        <AlertDialogDescription>
                                            You&apos;ll need your password and current MFA code.
                                        </AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <div className="space-y-3">
                                        <div>
                                            <Label htmlFor="dis-pwd">Password</Label>
                                            <Input id="dis-pwd" type="password" value={disablePwd} onChange={(e) => setDisablePwd(e.target.value)} data-testid="mfa-disable-password" />
                                        </div>
                                        <div>
                                            <Label htmlFor="dis-code">MFA code</Label>
                                            <Input id="dis-code" inputMode="numeric" value={disableCode} onChange={(e) => setDisableCode(e.target.value)} data-testid="mfa-disable-code" />
                                        </div>
                                    </div>
                                    <AlertDialogFooter>
                                        <AlertDialogCancel data-testid="dialog-cancel-button">Cancel</AlertDialogCancel>
                                        <AlertDialogAction onClick={disableMfa} data-testid="dialog-confirm-button">Disable MFA</AlertDialogAction>
                                    </AlertDialogFooter>
                                </AlertDialogContent>
                            </AlertDialog>
                        </div>
                    )}
                </div>

                <div className="rounded-xl border bg-card p-6">
                    <div className="text-base font-semibold">Account details</div>
                    <dl className="mt-4 space-y-3 text-sm">
                        <div className="flex justify-between"><dt className="text-muted-foreground">Email</dt><dd className="font-medium">{user?.email}</dd></div>
                        <div className="flex justify-between"><dt className="text-muted-foreground">Role</dt><dd className="font-medium">{user?.role}</dd></div>
                        <div className="flex justify-between"><dt className="text-muted-foreground">Tenant</dt><dd className="font-medium">{user?.tenant_name || "—"}</dd></div>
                        <div className="flex justify-between"><dt className="text-muted-foreground">MFA</dt><dd className="font-medium">{user?.mfa_enabled ? "Enabled" : user?.mfa_required ? "Required (not yet enrolled)" : "Optional"}</dd></div>
                    </dl>
                </div>
            </div>
        </AppShell>
    );
}
