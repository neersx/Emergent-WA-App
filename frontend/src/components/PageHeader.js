export function PageHeader({ title, description, breadcrumb, actions }) {
    return (
        <div className="mb-6">
            {breadcrumb && <div className="text-xs text-muted-foreground">{breadcrumb}</div>}
            <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1
                        className="text-2xl font-semibold tracking-tight"
                        data-testid="admin-page-title"
                    >
                        {title}
                    </h1>
                    {description && (
                        <p className="mt-1 text-sm text-muted-foreground">{description}</p>
                    )}
                </div>
                {actions && <div className="flex items-center gap-2">{actions}</div>}
            </div>
        </div>
    );
}
