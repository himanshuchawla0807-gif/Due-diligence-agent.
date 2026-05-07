# How to Use the Due Diligence Agent

## Getting Started

### 1. Start the Application

Make sure both backend and frontend are running:

**Terminal 1 - Backend:**
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8102
```

**Terminal 2 - Frontend:**
```bash
npm --prefix frontend run dev
```

Open your browser to: **http://localhost:5174**

---

## 2. Upload Files

When you first open the app, you'll see the **Upload Interface**:

### Upload Methods

#### Option A: Drag & Drop
1. Open your file explorer
2. Select files or folders
3. Drag them into the dashed upload area
4. Drop to upload

#### Option B: Choose Files Button
1. Click the blue **"Choose Files"** button
2. Select one or multiple files
3. Click "Open"

#### Option C: Choose Folder Button
1. Click the purple **"Choose Folder"** button
2. Select a folder (all contents will be uploaded)
3. Click "Select Folder"

### Supported Uploads
- ✅ Individual files (PDF, DOCX, XLSX, TXT, etc.)
- ✅ Multiple files at once
- ✅ Entire folders with nested subdirectories
- ✅ Zip archives
- ✅ Large batches (20+, 50+, 100+ files)

### Upload Process

1. **Initial State:** Drag or click to upload
2. **Uploading:** Spinner animation shows progress
3. **Success:** Green checkmark appears
4. **Transition:** Automatically moves to chat interface

---

## 3. Chat with Your Documents

After upload completes:

### View Uploaded Files

- **File pills appear** above the chat input
- **Top 3 files** are displayed
- **Remaining files** shown as "+X more"

Example:
```
[📄 investment_memo.pdf] [📄 financial_report.xlsx] [📄 pitch_deck.pdf] [+5 more]
```

### Remove Files

1. Hover over any file pill
2. Click the **X button** that appears
3. File is removed from the session

**Note:** If you remove all files, you'll return to the upload screen.

---

## 4. Ask Questions

### Using the Chat Input

The input box supports:

**Basic queries:**
- Type your question
- Press **Enter** to send
- Use **Shift+Enter** for new lines

**Web Search Toggle:**
- Click the globe icon to enable/disable web search
- When enabled, queries will search the web (future feature)

**File Attachment:**
- Click the paperclip icon to attach additional files during chat

### Example Queries

For financial due diligence:
```
What are the key financial metrics in the uploaded documents?
Summarize the risk factors mentioned in the investment memo.
What is the company's revenue growth over the last 3 years?
```

For document analysis:
```
Extract all names and contacts from the uploaded files.
What are the main objectives in the pitch deck?
Summarize the key points from all uploaded documents.
```

---

## 5. Connection Status

**Top-right indicator** shows backend connection:

- 🟢 **Connected** - Ready to process queries
- 🟡 **Checking...** - Verifying connection
- 🔴 **Offline** - Backend not available

---

## Tips & Best Practices

### For Best Results

1. **Upload all related documents together**
   - Better context for AI analysis
   - More comprehensive answers

2. **Organize files clearly**
   - Use descriptive filenames
   - Group related documents in folders

3. **Supported formats**
   - PDF, DOCX, XLSX, TXT, CSV
   - Zip archives (will be extracted)
   - Image files (JPG, PNG)

### Large Data Rooms

For due diligence with 20-50 documents:

1. **Organize in folders:**
   ```
   Due_Diligence/
   ├── Financials/
   │   ├── Q1_2024.pdf
   │   ├── Q2_2024.pdf
   │   └── Annual_Report.pdf
   ├── Legal/
   │   ├── Contracts/
   │   └── Compliance/
   ├── HR/
   │   └── Employee_Reviews/
   └── Pitch_Decks/
   ```

2. **Upload the entire "Due_Diligence" folder**
   - All nested files will be included
   - Maintains organization

3. **Ask comprehensive questions**
   - AI can search across all documents
   - Provides consolidated insights

---

## Troubleshooting

### Upload Issues

**Files not uploading?**
- Check file size (very large files may take time)
- Try uploading in smaller batches
- Check browser console for errors

**Upload stuck?**
- Refresh the page
- Try again with fewer files
- Check your internet connection

### Chat Issues

**Not seeing uploaded files?**
- Wait for "Upload Complete" message
- Check that upload finished successfully
- Refresh if needed

**Backend offline?**
- Check connection status (top-right)
- Ensure backend is running on port 8000
- Run: `python backend/main.py`

---

## Keyboard Shortcuts

- **Enter** - Send message
- **Shift + Enter** - New line in message
- **Esc** - (Future: Cancel upload)

---

## What Happens to Your Files?

**Currently (Frontend Only):**
- Files are stored in browser memory
- Not sent to backend yet
- Lost on page refresh

**Future (With Backend):**
- Files uploaded to server
- Processed and indexed
- Searchable via AI
- Securely stored
- Can be downloaded later

---

## Next Session

When you return:
- Upload screen will appear again
- Previous files not retained (yet)
- Upload fresh files for new analysis

**Future:** Session persistence, file history, saved conversations.

