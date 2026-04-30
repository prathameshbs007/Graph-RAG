# UI Components Visual Guide

## 1. Header Navigation

```
┌─────────────────────────────────────────────────────────────────┐
│  R  ResearchOS              🔍 Search  📊 Graph  📤 Ingest  | 🗑️ Clear DB  │
│      Graph RAG v2.0                                            │
└─────────────────────────────────────────────────────────────────┘
```

- Sticky top navigation with gradient logo
- Active tab highlighted with gradient background
- Clear DB button on the right with confirmation

## 2. Search Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│          Intelligent Research Search                           │
│     Ask questions about your documents, papers...              │
│                                                                 │
│    ┌───────────────────────────────────────────────────────┐   │
│    │ 🔍  Search query here...              [Search]        │   │
│    └───────────────────────────────────────────────────────┘   │
│                                                                 │
│    [Main concepts] [Relationships] [Summarize]                │
│                                                                 │
│          📚 Upload Documents   🔍 Smart Search   📊 Graph      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Search Results - Answer Card

```
┌────────────────────────────────────────────────────────────────────┐
│  💡 Research Answer                                                │
│     Evidence-based insights from your knowledge graph             │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─ Your Answer Here ───────────────────────────────────────┐    │
│  │ This is a detailed answer based on the retrieved sources │    │
│  │ and visual evidence from your documents.                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                    │
│  ┌─ Cited Sources [3] ──┐   ┌─ Visual Evidence [2] ──┐           │
│  │ [1] 📄 Paper Title    │   │ 📷 Figure Caption      │           │
│  │     Authors (2024)    │   │    Page 5              │           │
│  │     Relevance: 95%    │   │                        │           │
│  │     "Quote..."        │   ├─ Figure 2 Caption ────┤           │
│  │                       │   │    Page 8              │           │
│  │ [2] 🎵 Audio Title    │   └────────────────────────┘           │
│  │     Relevance: 87%    │                                        │
│  │     "Transcript..."   │                                        │
│  └───────────────────────┘                                        │
│                                                                    │
│  ✓ 3 sources • 2 figures • Based on latest research              │
└────────────────────────────────────────────────────────────────────┘
```

## 4. Upload Panel

```
┌────────────────────────────────────────────────────────────────┐
│          Ingest Content                                        │
│  Upload PDFs and audio files to build your knowledge graph    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                          📁                               │ │
│  │      Drag & drop your file here                         │ │
│  │         or click to select a PDF or audio file          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  Title                                                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Enter title (optional)                                │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                │
│  Authors (optional for PDF)                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Author1, Author2, Author3                             │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                │
│         ┌──────────────────────────────────────┐              │
│         │  Processing: 75%  ▓▓▓▓▓▓▓▓░░░░     │              │
│         └──────────────────────────────────────┘              │
│                                                                │
│    ┌─────────────────────────────────────────────────────┐   │
│    │       📤  Upload & Ingest                          │   │
│    └─────────────────────────────────────────────────────┘   │
│                                                                │
│  ✅ Success                                                    │
│  {"paper_id": "uuid...", "chunks_created": 45, ...}          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## 5. Clear DB Button States

### Normal State

```
┌──────────────┐
│ 🗑️ Clear DB  │
└──────────────┘
```

### Hover State

```
┌──────────────┐
│ 🗑️ Clear DB  │  ← shadow effect
└──────────────┘
```

### Confirmation Modal

```
┌──────────────────────────────────────────┐
│ Clear Database?                          │
├──────────────────────────────────────────┤
│ This will delete all documents, audio    │
│ files, and graphs. This action cannot be │
│ undone.                                  │
├──────────────────────────────────────────┤
│  [Cancel]           [Confirm]            │
└──────────────────────────────────────────┘
```

### After Confirmation

```
┌──────────────────────────────────────────┐
│ Confirming...                            │
│ ┌──────────────────────────────────────┐ │
│ │ 🔄 Clearing                          │ │
│ └──────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

### Success

```
┌──────────────────────────────────────────┐
│ ✓ Database cleared successfully          │
└──────────────────────────────────────────┘
```

## 6. Source Chip Example

```
┌────────────────────────────────────────────┐
│ 📄 [1] Paper        │ Relevance: 95%      │
├────────────────────────────────────────────┤
│ Attention Is All You Need                  │
│ Vaswani, A. et al. • 2017                 │
├────────────────────────────────────────────┤
│ "The dominant sequence transduction models │
│ are based on complex recurrent or           │
│ convolutional neural networks..."          │
└────────────────────────────────────────────┘
```

## 7. Figure Citation Example

```
┌──────────────────────────┐
│  ┌────────────────────┐  │
│  │   [Image Preview]  │  │
│  │    (hover to zoom) │  │
│  └────────────────────┘  │
├──────────────────────────┤
│ Paper: Attention Study   │
│ Caption: Attention       │
│ mechanism visualization  │
│ 📄 Page 3   Figure       │
└──────────────────────────┘
```

## Color Palette

| Element        | Color      | RGB            |
| -------------- | ---------- | -------------- |
| Primary Button | Blue 600   | `#2563eb`      |
| Secondary      | Indigo 600 | `#4f46e5`      |
| Success        | Green 600  | `#16a34a`      |
| Danger         | Red 600    | `#dc2626`      |
| Warning        | Amber 600  | `#d97706`      |
| Background     | Gradient   | Slate → Indigo |

## Responsive Breakpoints

- **Mobile**: Full width, single column
- **Tablet**: 2 columns for results
- **Desktop**: Full grid layout with optimal spacing
