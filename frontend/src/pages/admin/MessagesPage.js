import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { MessageSquareText, Send, RefreshCcw } from "lucide-react";
import { Link } from "react-router-dom";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export default function MessagesPage() {
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    const load = async () => {
        setRefreshing(true);
        try {
            const r = await api.get("/messages?limit=100");
            setMessages(r.data);
        } catch (err) {
            toast.error("Failed to load messages");
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        load();
        const id = setInterval(load, 4000);
        return () => clearInterval(id);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const simulate = async (messageId, event) => {
        try {
            await api.post(`/messages/${messageId}/simulate-webhook`, { message_id: messageId, event });
            toast.success(`Simulated ${event} webhook queued. Status will update shortly.`);
            setTimeout(load, 800);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Simulation failed");
        }
    };

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Admin / Message Log</span>}
                title="Message Log"
                description="Outbound + inbound messages. Auto-refreshes every 4 seconds."
                actions={
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={load} disabled={refreshing} data-testid="messages-refresh-button">
                            <RefreshCcw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} /> Refresh
                        </Button>
                        <Button asChild data-testid="messages-send-cta">
                            <Link to="/app/send">
                                <Send className="mr-2 h-4 w-4" /> Send Template
                            </Link>
                        </Button>
                    </div>
                }
            />
            {loading ? (
                <div className="h-40 animate-pulse rounded-xl border bg-card" />
            ) : messages.length === 0 ? (
                <EmptyState
                    icon={MessageSquareText}
                    title="No messages yet"
                    description="Send your first template message to populate the log."
                    action={
                        <Button asChild data-testid="empty-state-primary-action">
                            <Link to="/app/send">Send template</Link>
                        </Button>
                    }
                />
            ) : (
                <div className="overflow-hidden rounded-xl border bg-card">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Direction</TableHead>
                                <TableHead>Recipient</TableHead>
                                <TableHead>Template</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Sent</TableHead>
                                <TableHead>Delivered</TableHead>
                                <TableHead>Read</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {messages.map((m) => (
                                <TableRow key={m.id} data-testid="message-row">
                                    <TableCell className="text-xs uppercase">{m.direction}</TableCell>
                                    <TableCell>
                                        <div className="font-medium">{m.to_wa_id || m.from_wa_id || "—"}</div>
                                        <div className="font-mono text-[10px] text-muted-foreground">{(m.meta_message_id || "").slice(0, 20)}</div>
                                    </TableCell>
                                    <TableCell>
                                        <div className="text-sm">{m.template_name || "—"}</div>
                                        <div className="text-[10px] text-muted-foreground">{m.language_code}</div>
                                    </TableCell>
                                    <TableCell><StatusBadge status={m.status} /></TableCell>
                                    <TableCell className="text-xs text-muted-foreground">{m.sent_at ? new Date(m.sent_at).toLocaleTimeString() : "—"}</TableCell>
                                    <TableCell className="text-xs text-muted-foreground">{m.delivered_at ? new Date(m.delivered_at).toLocaleTimeString() : "—"}</TableCell>
                                    <TableCell className="text-xs text-muted-foreground">{m.read_at ? new Date(m.read_at).toLocaleTimeString() : "—"}</TableCell>
                                    <TableCell className="text-right">
                                        {m.direction === "outbound" && m.meta_message_id && (
                                            <DropdownMenu>
                                                <DropdownMenuTrigger asChild>
                                                    <Button size="sm" variant="outline" data-testid="message-simulate-trigger">Simulate →</Button>
                                                </DropdownMenuTrigger>
                                                <DropdownMenuContent align="end">
                                                    <DropdownMenuItem onClick={() => simulate(m.id, "delivered")} data-testid="simulate-delivered">Delivered</DropdownMenuItem>
                                                    <DropdownMenuItem onClick={() => simulate(m.id, "read")} data-testid="simulate-read">Read</DropdownMenuItem>
                                                    <DropdownMenuItem onClick={() => simulate(m.id, "failed")} data-testid="simulate-failed">Failed</DropdownMenuItem>
                                                </DropdownMenuContent>
                                            </DropdownMenu>
                                        )}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            )}
        </AppShell>
    );
}
