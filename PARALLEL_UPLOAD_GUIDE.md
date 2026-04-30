# Parallel Upload Processing Guide

## Overview
The upload system now supports **parallel processing** with uploads continuing in the background even when you switch between tabs.

## How It Works

### Architecture
1. **UploadContext.tsx** - Global React Context managing upload queue state
2. **useUploadQueue.ts** - Custom hook that:
   - Manages upload tasks (pending, uploading, completed, error states)
   - Limits concurrent uploads to MAX 2 parallel uploads
   - Automatically processes queue when new tasks are added
   - Persists across tab switches

3. **UploadNotification.tsx** - Floating notification panel showing:
   - Active uploads (with progress bar)
   - Pending uploads (queued)
   - Completed uploads (success/error)

4. **UploadPanel.tsx** - Updated to use global context instead of local state

### Features
✅ **2 Concurrent Uploads** - Maximum 2 files upload in parallel
✅ **Persistent Processing** - Uploads continue when switching tabs
✅ **Queue Management** - Queued uploads process automatically
✅ **Real-time Notifications** - See progress of all uploads
✅ **Error Handling** - Failed uploads show error state with details

## Testing the Feature

### Test Case 1: Basic Parallel Upload
1. Go to **Upload** tab
2. Upload PDF file #1
3. Immediately upload PDF file #2 (within 1-2 seconds)
4. **Expected**: Both show as "uploading" in the UploadNotification panel
5. Check the notification panel - should show 2 active uploads with progress bars

### Test Case 2: Tab Switching During Upload
1. Upload multiple PDF files (3-4 files)
2. Click on **Search** tab immediately after starting uploads
3. **Expected**: 
   - UploadNotification panel stays visible
   - 2 files continue uploading in background
   - Remaining files show as "pending" in queue
   - Progress updates in real-time even on Search tab

### Test Case 3: Queue Processing
1. Upload 4 files rapidly
2. Watch the UploadNotification panel
3. **Expected sequence**:
   - Files 1-2: Show as "uploading" (active)
   - Files 3-4: Show as "pending" (in queue)
   - As files 1-2 complete, files 3-4 automatically start uploading

### Test Case 4: Mixed File Types
1. Upload a PDF file
2. While uploading, upload an audio file
3. Switch to a different tab
4. **Expected**: 
   - Both files process in parallel if under 2 concurrent limit
   - Different endpoints called (/ingest/pdf vs /ingest/audio)
   - Both complete successfully

## Code Locations

### Core Files Modified
- `frontend/src/contexts/UploadContext.tsx` - Global state provider
- `frontend/src/hooks/useUploadQueue.ts` - Queue logic
- `frontend/src/components/UploadPanel.tsx` - Updated to use context
- `frontend/src/components/UploadNotification.tsx` - Progress display
- `frontend/src/App.tsx` - Wrapped with UploadProvider

### Key Implementation Details
```typescript
// Max concurrent uploads
const MAX_CONCURRENT_UPLOADS = 2;

// Task states
type TaskState = "pending" | "uploading" | "completed" | "error";

// Automatic processing
processQueue() - Runs when tasks change, enforces 2-upload limit
```

## Configuration

### To Change Max Concurrent Uploads
Edit `frontend/src/hooks/useUploadQueue.ts`:
```typescript
const MAX_CONCURRENT_UPLOADS = 2; // Change this number (1-5 recommended)
```

### To Modify Upload Notification Position
Edit `frontend/src/components/UploadNotification.tsx`:
```tsx
className="fixed bottom-4 right-4" // Adjust positioning
```

## Troubleshooting

### Uploads Stop After Tab Switch
- Check browser console for errors
- Verify UploadProvider is wrapping App in main.tsx
- Ensure useUploadContext hook is called inside UploadProvider

### Notification Not Showing
- Verify UploadNotification is rendered in App.tsx (after main content)
- Check z-index conflicts with other fixed elements
- Clear browser cache and reload

### Only 1 Upload at a Time
- Check MAX_CONCURRENT_UPLOADS setting
- Verify processQueue() is being called after addTask()
- Check backend endpoint response times (slow responses limit parallelism)

## Performance Notes
- Concurrent limit of 2 balances performance with server load
- Network bandwidth is the bottleneck for large files
- Backend can handle 2+ simultaneous /ingest requests
- Each upload independently processes (PDFs extracted, audio transcribed)

## Future Enhancements
- [ ] Pause/Resume individual uploads
- [ ] Download upload history report
- [ ] Retry failed uploads automatically
- [ ] Drag-and-drop multiple files
- [ ] Upload progress breakdown (extract → embed → ingest)
