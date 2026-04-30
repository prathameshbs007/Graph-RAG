# Quick Start Guide 🚀

## Setup & Run

### Step 1: Start Backend

```bash
cd backend
python main.py
# Or with conda: conda activate your_env && python main.py
# Server runs at http://localhost:8054
```

### Step 2: Start Frontend

```bash
cd frontend
npm install  # if needed
npm run dev
# App runs at http://localhost:5173 (or shown in terminal)
```

### Step 3: Access UI

Open browser → `http://localhost:5173`

---

## Features at a Glance 🎯

### 🔍 Search Tab

1. Type your question in the beautiful search bar
2. Use quick suggestion pills or write custom query
3. Click **Search** button
4. View AI-generated answer with:
   - Cited sources (papers/audio)
   - Relevance scores
   - Visual evidence (figures)
   - Direct quotes

### 📤 Ingest Tab

1. Drag & drop or click to upload PDF or audio file
2. Fill optional metadata (title, authors, year)
3. Watch progress bar
4. See success message with ingestion details
5. Switch to Search to query your new document

### 📊 Graph Tab

Visualize relationships between concepts, papers, and entities in your knowledge base

### 🗑️ Clear Database

1. Click **🗑️ Clear DB** button in header
2. Read the warning carefully
3. Click **Confirm** to proceed
4. Wait for success message
5. Database is now empty and ready for new data

---

## New Features Explained 📋

### Clear Database Button

- **Where**: Top right of header (red button)
- **What**: Safely delete all data from database
- **Safety**: Confirmation modal prevents accidents
- **Result**: Database reset to clean state

### Beautiful New UI Elements

- **Gradient backgrounds** throughout app
- **Smooth animations** on interactions
- **Better visual hierarchy** with colors
- **Responsive design** for all screen sizes
- **Loading indicators** during operations
- **Success/error messages** for feedback

---

## Common Tasks 💼

### Upload a PDF

```
1. Click 📤 Ingest
2. Drag PDF into upload zone
3. (Optional) Enter title/authors/year
4. Click Upload & Ingest
5. Wait for success message
```

### Upload Audio

```
1. Click 📤 Ingest
2. Drag MP3/WAV/M4A into upload zone
3. (Optional) Enter title and paper ID
4. Click Upload & Ingest
5. Wait for success message
```

### Search Documents

```
1. Click 🔍 Search
2. Type your question (e.g., "What is attention?")
3. Or click a suggestion pill
4. Click Search button
5. Read the answer with sources
```

### Clear Everything

```
1. Click 🗑️ Clear DB (red button)
2. Read warning: "This will delete all documents..."
3. Click Confirm
4. Wait for success message
5. All data is now gone
```

---

## Troubleshooting 🔧

### Backend won't start

```
❌ Error: Port 8054 already in use
✅ Solution: Kill process on port 8054 or use different port
```

### Frontend won't connect

```
❌ Error: Connection refused
✅ Solution: Make sure backend is running on port 8054
```

### Clear DB returns error

```
❌ Error: Cannot clear database
✅ Solution: Check backend logs, ensure databases are running
```

### Uploads failing

```
❌ Error: Upload failed
✅ Solution: Check file size, ensure it's valid PDF/audio
```

### Search returns no results

```
❌ Error: No results found
✅ Solution: Upload documents first, try different keywords
```

---

## Keyboard Shortcuts ⌨️

| Action         | Keys                                 |
| -------------- | ------------------------------------ |
| Search         | Type query + **Enter**               |
| Focus search   | **Ctrl/Cmd + K** (browser dependent) |
| Close modal    | **Esc**                              |
| Tab navigation | **Tab**                              |

---

## API Endpoints 🔌

### Clear Database

```http
POST http://localhost:8054/admin/clear-db
Content-Type: application/json

Response:
{
  "status": "success",
  "message": "Database cleared successfully"
}
```

### Upload PDF

```http
POST http://localhost:8054/ingest/pdf
Content-Type: multipart/form-data

Fields:
- file (required)
- title (optional)
- authors (optional)
- year (optional)
```

### Upload Audio

```http
POST http://localhost:8054/ingest/audio
Content-Type: multipart/form-data

Fields:
- file (required)
- title (optional)
- source_paper_id (optional)
```

### Search

```http
POST http://localhost:8054/query/search
Content-Type: application/json

{
  "query": "your question here"
}
```

---

## File Structure 📂

```
Graph-RAG-audio_fix/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AnswerCard.tsx ✨ (enhanced)
│   │   │   ├── ClearDBButton.tsx ✨ (new)
│   │   │   ├── FigureCitation.tsx ✨ (enhanced)
│   │   │   ├── GraphExplorer.tsx
│   │   │   ├── QueryBar.tsx ✨ (enhanced)
│   │   │   ├── SourceChip.tsx ✨ (enhanced)
│   │   │   └── UploadPanel.tsx ✨ (enhanced)
│   │   ├── App.tsx ✨ (enhanced)
│   │   └── main.tsx
│   └── package.json
│
├── backend/
│   ├── routers/
│   │   ├── admin.py ✨ (new - clear DB endpoint)
│   │   ├── ingest.py
│   │   ├── query.py
│   │   └── graph.py
│   ├── main.py ✨ (updated)
│   ├── requirements.txt
│   └── [other files]
│
├── UI_ENHANCEMENTS.md (documentation)
├── BACKEND_CHANGES.md (documentation)
├── UI_GUIDE.md (documentation)
├── IMPLEMENTATION_CHECKLIST.md (documentation)
└── QUICK_START.md (this file)
```

---

## Configuration 🛠️

### Frontend Environment (.env)

```
VITE_API_URL=http://localhost:8054
```

### Backend Environment (.env)

```
WEAVIATE_URL=http://localhost:8080
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

---

## Performance Tips ⚡

1. **Clear database** before testing with large datasets
2. **Batch uploads** instead of uploading one file at a time
3. **Use specific queries** instead of very broad questions
4. **Monitor console** for any warnings or errors

---

## Production Checklist ✅

- [ ] Environment variables set
- [ ] HTTPS enabled
- [ ] Database backups configured
- [ ] Error logging set up
- [ ] Rate limiting configured
- [ ] CORS properly configured
- [ ] Input validation enabled
- [ ] User authentication added (if needed)

---

## Support & Help 💬

For issues or questions:

1. Check the logs (frontend console, backend terminal)
2. Review error messages carefully
3. Check documentation files:
   - `UI_ENHANCEMENTS.md` - UI details
   - `BACKEND_CHANGES.md` - Backend details
   - `UI_GUIDE.md` - Visual guide
4. Verify all services are running

---

## What's New? 🎉

✨ **Beautiful gradient UI** throughout the application
✨ **Smooth animations** for better UX
✨ **Clear Database button** with safety confirmation
✨ **Enhanced components** with improved styling
✨ **Better error handling** with visual feedback
✨ **Loading states** for all operations
✨ **Responsive design** for all devices
✨ **Professional appearance** with modern colors

---

**Version**: 2.0 - UI Enhanced + Clear DB Feature
**Status**: ✅ Ready to Use
**Last Updated**: May 2024

Enjoy your enhanced ResearchOS! 🚀
