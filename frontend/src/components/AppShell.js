import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    LayoutDashboard,
    Plug,
    Smartphone,
    Send,
    MessageSquareText,
    ShieldCheck,
    LogOut,
    User,
    MessageCircle,
    Menu,
    X,
    FileText,
    Inbox,
    BarChart3,
    Settings,
} from "lucide-react";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const nav = [
    { to: "/app/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/app/connect", label: "Connect WhatsApp", icon: Plug },
    { to: "/app/wabas", label: "WABAs & Numbers", icon: Smartphone },
    { to: "/app/templates", label: "Templates", icon: FileText },
    { to: "/app/send", label: "Send Template", icon: Send },
    { to: "/app/messages", label: "Message Log", icon: MessageSquareText },
    { to: "/app/inbox", label: "Inbox", icon: Inbox },
    { to: "/app/analytics", label: "Analytics", icon: BarChart3 },
    { to: "/app/security", label: "Security", icon: ShieldCheck },
    { to: "/app/settings", label: "Settings", icon: Settings },
];

export default function AppShell({ children }) {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [open, setOpen] = useState(false);
    const [mockMode, setMockMode] = useState(null);

    useEffect(() => {
        api.get("/system/info").then(r => setMockMode(r.data.mock_mode)).catch(() => {});
    }, []);

    const handleLogout = async () => {
        await logout();
        navigate("/login");
    };

    return (
        <div className="min-h-screen bg-[hsl(210_33%_98%)]">
            {/* Sidebar */}
            <aside
                className={cn(
                    "fixed inset-y-0 left-0 z-50 w-72 bg-[hsl(222_47%_11%)] text-[hsl(210_40%_98%)] transition-transform lg:translate-x-0",
                    open ? "translate-x-0" : "-translate-x-full",
                )}
                data-testid="admin-sidebar"
            >
                <div className="flex h-16 items-center justify-between border-b border-white/10 px-5">
                    <Link to="/app/dashboard" className="flex items-center gap-2" data-testid="admin-logo-link">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                            <MessageCircle className="h-4 w-4" />
                        </div>
                        <div>
                            <div className="text-sm font-semibold tracking-tight">WABA Console</div>
                            <div className="text-xs text-slate-400">Tech Provider</div>
                        </div>
                    </Link>
                    <button
                        className="lg:hidden"
                        onClick={() => setOpen(false)}
                        aria-label="Close sidebar"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>
                <nav className="px-3 py-4">
                    {nav.map((item) => {
                        const active = location.pathname.startsWith(item.to);
                        const Icon = item.icon;
                        return (
                            <Link
                                key={item.to}
                                to={item.to}
                                onClick={() => setOpen(false)}
                                data-testid={`admin-nav-${item.to.split("/").pop()}`}
                                className={cn(
                                    "group mb-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                                    "text-slate-200 hover:bg-white/10",
                                    active && "bg-white/15 text-white",
                                )}
                            >
                                <Icon className="h-4 w-4 opacity-90" />
                                <span>{item.label}</span>
                            </Link>
                        );
                    })}
                </nav>
                <div className="absolute bottom-4 left-3 right-3 rounded-lg bg-white/5 p-3 text-xs text-slate-300">
                    {mockMode === false ? (
                        <>
                            <div className="font-medium text-green-400">Live mode</div>
                            <div className="mt-1 leading-relaxed text-slate-400">
                                Real Meta API calls enabled. Webhooks are active.
                            </div>
                        </>
                    ) : (
                        <>
                            <div className="font-medium text-white">Mock mode</div>
                            <div className="mt-1 leading-relaxed text-slate-400">
                                Meta API calls are stubbed. Use simulated webhooks to test the full flow.
                            </div>
                        </>
                    )}
                </div>
            </aside>

            {/* Main */}
            <div className="lg:pl-72">
                {/* Topbar */}
                <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b bg-background/90 px-4 backdrop-blur sm:px-6 lg:px-8">
                    <div className="flex items-center gap-3">
                        <button
                            className="lg:hidden"
                            onClick={() => setOpen(true)}
                            aria-label="Open sidebar"
                            data-testid="admin-sidebar-open"
                        >
                            <Menu className="h-5 w-5" />
                        </button>
                        <div>
                            <div className="text-xs text-muted-foreground">Tenant</div>
                            <div className="text-sm font-medium" data-testid="admin-tenant-name">
                                {user?.tenant_name || "—"}
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        {mockMode !== null && (
                            <span
                                className={`rounded-full border px-2.5 py-0.5 text-xs font-medium inline-flex ${
                                    mockMode
                                        ? "bg-[hsl(38_92%_95%)] text-[hsl(38_92%_28%)]"
                                        : "bg-[hsl(152_55%_93%)] text-[hsl(152_55%_26%)]"
                                }`}
                                data-testid="admin-mock-badge"
                            >
                                {mockMode ? "MOCK MODE" : "LIVE MODE"}
                            </span>
                        )}
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="sm" data-testid="admin-user-menu">
                                    <User className="mr-2 h-4 w-4" />
                                    {user?.email}
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-56">
                                <DropdownMenuLabel>{user?.full_name || user?.email}</DropdownMenuLabel>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onClick={() => navigate("/app/security")} data-testid="admin-menu-security">
                                    <ShieldCheck className="mr-2 h-4 w-4" /> Security & MFA
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onClick={handleLogout} data-testid="admin-menu-logout">
                                    <LogOut className="mr-2 h-4 w-4" /> Sign out
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>
                </header>

                <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
            </div>

            {open && (
                <div
                    className="fixed inset-0 z-40 bg-black/40 lg:hidden"
                    onClick={() => setOpen(false)}
                />
            )}
        </div>
    );
}
