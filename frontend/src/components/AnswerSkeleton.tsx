export const AnswerSkeleton = () => (
    <div className="animate-pulse bg-surface-raised border border-border-default rounded-xl p-6 sm:p-8 shadow-sm w-full" aria-hidden="true">
        <div className="space-y-3 mb-8">
            <div className="h-4 bg-surface-hover rounded w-full" />
            <div className="h-4 bg-surface-hover rounded w-5/6" />
            <div className="h-4 bg-surface-hover rounded w-4/6" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-2">
                <div className="h-3 bg-surface-hover rounded w-1/3 mb-3" />
                <div className="h-16 bg-surface-hover rounded-lg" />
                <div className="h-16 bg-surface-hover rounded-lg" />
            </div>
            <div className="space-y-2">
                <div className="h-3 bg-surface-hover rounded w-1/3 mb-3" />
                <div className="h-32 bg-surface-hover rounded-lg" />
            </div>
        </div>
    </div>
);
