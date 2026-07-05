import { Link } from "react-router-dom";
import { MessageCircle } from "lucide-react";

export function AuthLayout({ title, subtitle, children, footer }) {
    return (
        <div className="min-h-screen bg-background">
            <div className="mx-auto grid min-h-screen max-w-6xl grid-cols-1 lg:grid-cols-2">
                <div className="flex flex-col px-4 py-10 sm:px-8">
                    <Link to="/" className="flex items-center gap-2" data-testid="auth-logo-link">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                            <MessageCircle className="h-4 w-4" />
                        </div>
                        <span className="text-sm font-semibold tracking-tight">WABA Console</span>
                    </Link>
                    <div className="flex flex-1 items-center justify-center">
                        <div className="w-full max-w-md">
                            <div className="mb-6">
                                <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
                                {subtitle && <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>}
                            </div>
                            <div className="rounded-2xl border bg-card p-6 sm:p-8 shadow-[0_18px_50px_-30px_hsl(222_47%_11%/0.35)]">
                                {children}
                            </div>
                            {footer && <div className="mt-6 text-center text-sm text-muted-foreground">{footer}</div>}
                        </div>
                    </div>
                </div>
                <div className="relative hidden overflow-hidden border-l bg-noise lg:block" />
            </div>
        </div>
    );
}
