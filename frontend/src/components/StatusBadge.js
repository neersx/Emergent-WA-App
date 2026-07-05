import { cn } from "@/lib/utils";

const variants = {
    queued:
        "bg-[hsl(215_20%_94%)] text-[hsl(215_25%_25%)] border-[hsl(215_18%_86%)]",
    sent: "bg-[hsl(199_95%_94%)] text-[hsl(199_80%_28%)] border-[hsl(199_70%_86%)]",
    delivered:
        "bg-[hsl(152_55%_93%)] text-[hsl(152_55%_26%)] border-[hsl(152_40%_84%)]",
    read: "bg-[hsl(238_85%_95%)] text-[hsl(238_55%_35%)] border-[hsl(238_55%_88%)]",
    failed: "bg-[hsl(0_90%_96%)] text-[hsl(0_70%_40%)] border-[hsl(0_70%_88%)]",
};

export function StatusBadge({ status }) {
    const v = variants[status] || variants.queued;
    return (
        <span
            data-testid="message-status-badge"
            className={cn(
                "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize",
                v,
            )}
        >
            {status}
        </span>
    );
}
