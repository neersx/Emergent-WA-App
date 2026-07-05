import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { MessageCircle, Menu, X } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

export function MarketingNav() {
    const [open, setOpen] = useState(false);
    return (
        <nav
            data-testid="marketing-nav"
            className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60"
        >
            <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
                <Link to="/" className="flex items-center gap-2" data-testid="marketing-logo-link">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                        <MessageCircle className="h-4 w-4" />
                    </div>
                    <span className="text-sm font-semibold tracking-tight">WABA Console</span>
                </Link>
                <div className="hidden items-center gap-6 md:flex">
                    <Link to="/features" className="text-sm text-muted-foreground hover:text-foreground" data-testid="marketing-nav-features">Features</Link>
                    <Link to="/pricing" className="text-sm text-muted-foreground hover:text-foreground" data-testid="marketing-nav-pricing">Pricing</Link>
                    <Link to="/contact" className="text-sm text-muted-foreground hover:text-foreground" data-testid="marketing-nav-contact">Contact</Link>
                </div>
                <div className="hidden items-center gap-2 md:flex">
                    <Button asChild variant="ghost" size="sm" data-testid="marketing-nav-signin-button">
                        <Link to="/login">Sign in</Link>
                    </Button>
                    <Button asChild size="sm" data-testid="marketing-nav-get-started-button">
                        <Link to="/register">Get started</Link>
                    </Button>
                </div>
                <button
                    className="md:hidden"
                    onClick={() => setOpen((v) => !v)}
                    aria-label="Toggle menu"
                    data-testid="marketing-nav-mobile-toggle"
                >
                    {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
                </button>
            </div>
            <div
                className={cn(
                    "border-t bg-background md:hidden",
                    open ? "block" : "hidden",
                )}
            >
                <div className="flex flex-col gap-1 px-4 py-3">
                    <Link to="/features" className="py-2 text-sm" onClick={() => setOpen(false)}>Features</Link>
                    <Link to="/pricing" className="py-2 text-sm" onClick={() => setOpen(false)}>Pricing</Link>
                    <Link to="/contact" className="py-2 text-sm" onClick={() => setOpen(false)}>Contact</Link>
                    <div className="mt-2 flex gap-2">
                        <Button asChild variant="outline" className="flex-1">
                            <Link to="/login">Sign in</Link>
                        </Button>
                        <Button asChild className="flex-1">
                            <Link to="/register">Get started</Link>
                        </Button>
                    </div>
                </div>
            </div>
        </nav>
    );
}

export function MarketingFooter() {
    return (
        <footer className="border-t bg-card">
            <div className="mx-auto grid max-w-6xl gap-8 px-4 py-12 sm:px-6 lg:grid-cols-4 lg:px-8">
                <div>
                    <div className="flex items-center gap-2">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                            <MessageCircle className="h-4 w-4" />
                        </div>
                        <span className="text-sm font-semibold">WABA Console</span>
                    </div>
                    <p className="mt-3 text-sm text-muted-foreground">
                        The Tech Provider control plane for WhatsApp Business Platform.
                    </p>
                </div>
                <div>
                    <div className="text-sm font-semibold">Product</div>
                    <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                        <li><Link to="/features">Features</Link></li>
                        <li><Link to="/pricing">Pricing</Link></li>
                        <li><Link to="/register">Get started</Link></li>
                    </ul>
                </div>
                <div>
                    <div className="text-sm font-semibold">Resources</div>
                    <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                        <li>Docs</li>
                        <li>API reference</li>
                        <li>Status</li>
                    </ul>
                </div>
                <div>
                    <div className="text-sm font-semibold">Company</div>
                    <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                        <li><Link to="/contact">Contact</Link></li>
                        <li>Security</li>
                        <li>Privacy</li>
                    </ul>
                </div>
            </div>
            <div className="border-t">
                <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 py-4 text-xs text-muted-foreground sm:flex-row sm:px-6 lg:px-8">
                    <span>© {new Date().getFullYear()} WABA Console. All rights reserved.</span>
                    <span>Built on the FARM stack · Phase 1 MVP</span>
                </div>
            </div>
        </footer>
    );
}
