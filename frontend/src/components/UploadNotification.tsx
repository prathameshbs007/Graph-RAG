import { useUploadContext } from '../contexts/UploadContext';

export const UploadNotification = () => {
  const { tasks, removeTask, clearCompleted } = useUploadContext();

  const activeTasks = tasks.filter(t => t.status === 'uploading' || t.status === 'pending');
  const completedTasks = tasks.filter(t => t.status === 'completed');
  const errorTasks = tasks.filter(t => t.status === 'error');

  if (tasks.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 w-96 space-y-2.5 z-40 font-mono text-xs">
      {/* Active/Pending Uploads */}
      {activeTasks.map((task) => (
        <div
          key={task.id}
          className="bg-surface-container-low/95 border border-surface-container-highest/60 rounded-xl p-3.5 backdrop-blur-xl shadow-xl space-y-2"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0 pr-2">
              <p className="font-semibold text-on-surface truncate">
                {task.file.name}
              </p>
              <p className="text-[11px] text-outline mt-0.5 flex items-center gap-1">
                <span className="material-symbols-outlined text-[12px] animate-spin">sync</span>
                {task.status === 'uploading' ? 'Extracting & Ingesting...' : 'Queued'}
              </p>
            </div>
            {task.status === 'uploading' && (
              <span className="font-bold text-secondary">{task.progress}%</span>
            )}
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-surface-container-highest rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-secondary h-full transition-all duration-300"
              style={{ width: `${task.progress}%` }}
            ></div>
          </div>
        </div>
      ))}

      {/* Completed Tasks */}
      {completedTasks.map((task) => (
        <div
          key={task.id}
          className="bg-surface-container-low/95 border border-secondary/40 rounded-xl p-3 backdrop-blur-xl flex items-start justify-between group shadow-lg"
        >
          <div className="flex items-start gap-2.5 min-w-0">
            <span className="material-symbols-outlined text-secondary text-[1rem]">check_circle</span>
            <div className="min-w-0">
              <p className="font-semibold text-secondary-fixed truncate">
                {task.file.name}
              </p>
              <p className="text-[10px] text-outline mt-0.5">Ingested successfully</p>
            </div>
          </div>
          <button
            onClick={() => removeTask(task.id)}
            className="text-outline hover:text-on-surface p-1 transition-colors"
          >
            ✕
          </button>
        </div>
      ))}

      {/* Error Tasks */}
      {errorTasks.map((task) => (
        <div
          key={task.id}
          className="bg-surface-container-low/95 border border-error/40 rounded-xl p-3 backdrop-blur-xl flex items-start justify-between group shadow-lg"
        >
          <div className="flex items-start gap-2.5 min-w-0">
            <span className="material-symbols-outlined text-error text-[1rem]">error</span>
            <div className="min-w-0">
              <p className="font-semibold text-error truncate">
                {task.file.name}
              </p>
              <p className="text-[10px] text-error/80 mt-0.5">{task.error}</p>
            </div>
          </div>
          <button
            onClick={() => removeTask(task.id)}
            className="text-outline hover:text-on-surface p-1 transition-colors"
          >
            ✕
          </button>
        </div>
      ))}

      {/* Clear Button */}
      {(completedTasks.length > 0 || errorTasks.length > 0) && activeTasks.length === 0 && (
        <button
          onClick={clearCompleted}
          className="w-full text-[11px] font-semibold text-outline hover:text-on-surface py-1 text-center transition-colors"
        >
          Clear finished notifications
        </button>
      )}
    </div>
  );
};
