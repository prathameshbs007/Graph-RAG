import { useUploadContext } from '../contexts/UploadContext';

export const UploadNotification = () => {
  const { tasks, removeTask, clearCompleted } = useUploadContext();

  const activeTasks = tasks.filter(t => t.status === 'uploading' || t.status === 'pending');
  const completedTasks = tasks.filter(t => t.status === 'completed');
  const errorTasks = tasks.filter(t => t.status === 'error');

  if (tasks.length === 0) return null;

  return (
    <div className="fixed bottom-8 right-8 w-96 space-y-3 z-40">
      {/* Active/Pending Uploads */}
      {activeTasks.map((task) => (
        <div
          key={task.id}
          className="glass-dark border border-white/10 rounded-xl p-4 backdrop-blur-xl space-y-2"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-sm font-semibold text-white truncate">
                {task.file.name}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {task.status === 'uploading' ? 'Uploading...' : 'Queued'}
              </p>
            </div>
            {task.status === 'uploading' && (
              <span className="text-xs font-bold text-cyan-400">{task.progress}%</span>
            )}
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden">
            <div
              className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full transition-all duration-300"
              style={{ width: `${task.progress}%` }}
            ></div>
          </div>
        </div>
      ))}

      {/* Completed Tasks */}
      {completedTasks.map((task) => (
        <div
          key={task.id}
          className="glass-dark border border-green-500/30 rounded-xl p-4 backdrop-blur-xl flex items-start justify-between group hover:border-green-500/60 transition-colors"
        >
          <div className="flex items-start gap-3">
            <span className="text-xl">✓</span>
            <div>
              <p className="text-sm font-semibold text-green-300">
                {task.file.name}
              </p>
              <p className="text-xs text-gray-400 mt-1">Uploaded successfully</p>
            </div>
          </div>
          <button
            onClick={() => removeTask(task.id)}
            className="text-gray-400 hover:text-white transition-colors opacity-0 group-hover:opacity-100"
          >
            ✕
          </button>
        </div>
      ))}

      {/* Error Tasks */}
      {errorTasks.map((task) => (
        <div
          key={task.id}
          className="glass-dark border border-red-500/30 rounded-xl p-4 backdrop-blur-xl flex items-start justify-between group hover:border-red-500/60 transition-colors"
        >
          <div className="flex items-start gap-3">
            <span className="text-xl">✗</span>
            <div>
              <p className="text-sm font-semibold text-red-300">
                {task.file.name}
              </p>
              <p className="text-xs text-red-300/70 mt-1">{task.error}</p>
            </div>
          </div>
          <button
            onClick={() => removeTask(task.id)}
            className="text-gray-400 hover:text-white transition-colors opacity-0 group-hover:opacity-100"
          >
            ✕
          </button>
        </div>
      ))}

      {/* Clear Button */}
      {(completedTasks.length > 0 || errorTasks.length > 0) && activeTasks.length === 0 && (
        <button
          onClick={clearCompleted}
          className="w-full text-xs font-semibold text-gray-400 hover:text-white py-2 transition-colors"
        >
          Clear finished uploads
        </button>
      )}
    </div>
  );
};
