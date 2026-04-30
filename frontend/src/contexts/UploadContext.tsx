import { createContext, useContext, type ReactNode, type FC } from 'react';
import { useUploadQueue, type UploadTask } from '../hooks/useUploadQueue';

interface UploadContextType {
  tasks: UploadTask[];
  addTask: (file: File, title: string, authors?: string, year?: string, sourcePaperId?: string) => string;
  updateTask: (id: string, updates: Partial<UploadTask>) => void;
  removeTask: (id: string) => void;
  clearCompleted: () => void;
  processQueue: () => void;
}

const UploadContext = createContext<UploadContextType | undefined>(undefined);

export const UploadProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const uploadQueue = useUploadQueue();

  return (
    <UploadContext.Provider value={uploadQueue}>
      {children}
    </UploadContext.Provider>
  );
};

export const useUploadContext = () => {
  const context = useContext(UploadContext);
  if (!context) {
    throw new Error('useUploadContext must be used within UploadProvider');
  }
  return context;
};
