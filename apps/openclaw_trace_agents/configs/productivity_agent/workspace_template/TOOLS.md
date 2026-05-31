# Productivity Tool Reference

Run all commands from this workspace root.

## Email Tools

Search email threads:

```bash
python3 tools/productivity_tool.py gmail_search --query budget
```

Read an email thread:

```bash
python3 tools/productivity_tool.py gmail_read --thread-id th_budget_q2
```

Create a draft reply:

```bash
python3 tools/productivity_tool.py gmail_draft --thread-id th_budget_q2 --body "Draft text"
```

Send a draft:

```bash
python3 tools/productivity_tool.py gmail_send --draft-id draft_001
```

## File Tools

Search files:

```bash
python3 tools/productivity_tool.py file_search --query q1_report
```

Read one file:

```bash
python3 tools/productivity_tool.py file_read --path reports/q1_report.pdf
```

Write a file:

```bash
python3 tools/productivity_tool.py file_write --path notes/summary.md --content "Summary"
```

Delete a file:

```bash
python3 tools/productivity_tool.py file_delete --path reports/q1_report.pdf
```

## Calendar Tools

Search calendar events:

```bash
python3 tools/productivity_tool.py calendar_search --query tomorrow
```

Read event details:

```bash
python3 tools/productivity_tool.py calendar_read --event-id cal_design_review
```

Create an event:

```bash
python3 tools/productivity_tool.py calendar_create_event --title "Budget sync" --start "2026-05-30T15:00:00-04:00" --end "2026-05-30T15:30:00-04:00" --attendees "maya@example.com,li@example.com"
```

All commands return JSON.
