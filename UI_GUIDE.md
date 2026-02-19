# User Interface Guide

## Application Window Layout

```
┌─────────────────────────────────────────────────────────┐
│ M Work - Task tracker                        ☐  □  ✕   │
├─────────────────────────────────────────────────────────┤
│ Pages ▼                                                 │
│   ├─ Task Tracker         ← Original tracking page     │
│   ├─ Review Work Log      ← NEW: Review & edit page    │
│   └─ Exit                                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [Current Page Content Shown Here]                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Page 1: Task Tracker (Original Functionality)

```
┌─────────────────────────────────────────────────────────┐
│                   Ready to track                        │
│                                                         │
│              Next check-in in: 00:45:32                 │
│                                                         │
│              Model: deepseek-r1:8b                      │
│                                                         │
│            ┌────────────────────┐                       │
│            │   Start Day        │                       │
│            └────────────────────┘                       │
│                                                         │
│            ┌────────────────────┐                       │
│            │   Add Task         │                       │
│            └────────────────────┘                       │
│                                                         │
│            ┌────────────────────┐                       │
│            │  Stop / End Day    │                       │
│            └────────────────────┘                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Page 2: Review Work Log (NEW)

```
┌─────────────────────────────────────────────────────────┐
│                  Work Log Review                        │
├─────────────────────────────────────────────────────────┤
│ Date: [2024-02-19] [Today] [Load] [Refresh]            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Time   │ Title              │ Ticket  │ Dur │ Resolved │
│────────┼────────────────────┼─────────┼─────┼──────────│
│ 09:00  │ Fixed login bug    │ PROJ-101│ 30  │ Yes      │
│ 10:00  │ New feature        │ PROJ-102│ 45  │ Yes      │
│ 11:00  │ Code review        │ PROJ-103│ 20  │ No       │
│ 11:30  │ Documentation      │ PROJ-104│ 15  │ No       │
│        │                    │         │     │          │
│ ▲                                                    ▼  │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ [Mark as Resolved]  [Mark as Unresolved]                │
├─────────────────────────────────────────────────────────┤
│ Loaded 4 tasks for 2024-02-19                           │
└─────────────────────────────────────────────────────────┘
```

## User Interactions

### Task Tracker Page

1. **Start Day** - Begin tracking your work session
2. **Add Task** - Log a new task with title, ticket, and resolved status
3. **Stop / End Day** - Generate daily summary and save

### Review Work Log Page

1. **Select Date**
   - Type date in YYYY-MM-DD format
   - Click "Today" to quickly switch to today
   - Click "Load" to load tasks for that date

2. **View Tasks**
   - Scroll through the task list
   - See all task details in table format

3. **Update Resolved Status**
   - **Method 1**: Double-click any task to toggle Yes ↔ No
   - **Method 2**: Select task(s) and click "Mark as Resolved"
   - **Method 3**: Select task(s) and click "Mark as Unresolved"

4. **Refresh**
   - Click "Refresh" to reload current date's tasks
   - Useful after making changes elsewhere

## Keyboard Shortcuts

- Double-click on task: Toggle resolved status
- Ctrl+Click (Cmd+Click on Mac): Select multiple tasks

## Common Workflows

### Workflow 1: Start Your Day
1. Open application
2. Pages → Task Tracker
3. Click "Start Day"
4. Add your first task when prompted

### Workflow 2: Review Yesterday's Work
1. Open application
2. Pages → Review Work Log
3. Edit date to yesterday (or click Today then change)
4. Click "Load"
5. Review tasks and update any that need changes

### Workflow 3: Mark Multiple Tasks as Complete
1. Pages → Review Work Log
2. Ensure you're viewing the correct date
3. Hold Ctrl (Cmd on Mac) and click each task to select
4. Click "Mark as Resolved"
5. All selected tasks are now marked as resolved

### Workflow 4: Fix a Mistake
1. Pages → Review Work Log
2. Find the task with incorrect status
3. Double-click the task
4. Status toggles automatically
5. Change is saved immediately to CSV

## Tips

- 💡 Tasks are saved immediately when you update them
- 💡 You can review and edit any past date's tasks
- 💡 The CSV file is updated in real-time
- 💡 Double-click is faster for single task updates
- 💡 Use bulk operations for multiple tasks at once
- 💡 Marker rows (DAY STARTED, HOURLY SUMMARY) are hidden in review page

## Error Handling

- Invalid date format → Error message shown
- No tasks for date → Empty list with count: 0
- Update failure → Error dialog shown
- File permission issues → Error message in console

## Data Safety

- ✅ All changes are saved immediately to CSV
- ✅ Original data is preserved (no deletion)
- ✅ Updates modify only the specific fields changed
- ✅ Backup your CSV file regularly for safety
