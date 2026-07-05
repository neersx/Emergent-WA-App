import { Button } from "@/components/ui/button";

export function EmptyState({ icon: Icon, title, description, action }) {
    return (
        <div
            className="rounded-xl border bg-card p-10 text-center"
            data-testid="empty-state"
        >
            {Icon && <Icon className="mx-auto mb-4 h-10 w-10 text-primary" />}
            <div className="text-base font-semibold">{title}</div>
            {description && (
                <p className="mt-1 text-sm text-muted-foreground">{description}</p>
            )}
            {action && (
                <div className="mt-6 flex items-center justify-center gap-2">
                    {action}
                </div>
            )}
        </div>
    );
}
