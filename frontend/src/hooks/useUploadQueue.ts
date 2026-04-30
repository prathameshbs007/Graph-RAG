import { useState, useCallback, useRef } from 'react';

export interface UploadTask {
  id: string;
  file: File;
  title: string;
  authors?: string;
  year?: string;
  sourcePaperId?: string;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
  result?: any;
}

export const useUploadQueue = () => {
  const [tasks, setTasks] = useState<UploadTask[]>([]);
  const activeUploadsRef = useRef(0);
  const MAX_CONCURRENT_UPLOADS = 2;

  const updateTask = useCallback((id: string, updates: Partial<UploadTask>) => {
    setTasks((prev) =>
      prev.map((task) => (task.id === id ? { ...task, ...updates } : task))
    );
  }, []);

  const addTask = useCallback(
    (
      file: File,
      title: string,
      authors?: string,
      year?: string,
      sourcePaperId?: string
    ) => {
      const id = `upload-${Date.now()}-${Math.random()}`;
      const newTask: UploadTask = {
        id,
        file,
        title,
        authors,
        year,
        sourcePaperId,
        progress: 0,
        status: 'pending',
      };
      setTasks((prev) => [...prev, newTask]);
      return id;
    },
    []
  );

  const processNextTask = useCallback(
    async (pendingTask: UploadTask, updateFn: (id: string, updates: Partial<UploadTask>) => void) => {
      if (activeUploadsRef.current >= MAX_CONCURRENT_UPLOADS) return;

      activeUploadsRef.current++;
      updateFn(pendingTask.id, { status: 'uploading', progress: 10 });

      try {
        const formData = new FormData();
        formData.append('file', pendingTask.file);
        if (pendingTask.title) formData.append('title', pendingTask.title);

        const isAudio =
          pendingTask.file.type.startsWith('audio/') ||
          pendingTask.file.name.match(/\.(mp3|wav|m4a)$/i);

        if (isAudio) {
          if (pendingTask.sourcePaperId)
            formData.append('source_paper_id', pendingTask.sourcePaperId);
        } else {
          if (pendingTask.authors) formData.append('authors', pendingTask.authors);
          if (pendingTask.year) formData.append('year', pendingTask.year);
        }

        updateFn(pendingTask.id, { progress: 40 });

        const endpoint = isAudio ? '/ingest/audio' : '/ingest/pdf';
        const res = await fetch(`http://localhost:8054${endpoint}`, {
          method: 'POST',
          body: formData,
        });

        updateFn(pendingTask.id, { progress: 80 });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();
        updateFn(pendingTask.id, {
          progress: 100,
          status: 'completed' as const,
          result: data,
        });
      } catch (error) {
        updateFn(pendingTask.id, {
          status: 'error' as const,
          error: error instanceof Error ? error.message : 'Upload failed',
          progress: 100,
        });
      } finally {
        activeUploadsRef.current--;
      }
    },
    []
  );

  const processQueue = useCallback(() => {
    setTasks((currentTasks) => {
      const pendingTask = currentTasks.find((t) => t.status === 'pending');
      if (pendingTask && activeUploadsRef.current < MAX_CONCURRENT_UPLOADS) {
        processNextTask(pendingTask, (id, updates) => {
          setTasks((prev) =>
            prev.map((t) => (t.id === id ? { ...t, ...updates } : t))
          );
        });
      }
      return currentTasks;
    });
  }, [processNextTask]);

  const removeTask = useCallback((id: string) => {
    setTasks((prev) => prev.filter((task) => task.id !== id));
  }, []);

  const clearCompleted = useCallback(() => {
    setTasks((prev) =>
      prev.filter((task) => task.status !== 'completed' && task.status !== 'error')
    );
  }, []);

  return {
    tasks,
    addTask,
    updateTask,
    removeTask,
    clearCompleted,
    processQueue,
  };
};
