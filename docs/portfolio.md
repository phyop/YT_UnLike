# Portfolio collateral

## Resume bullets

- Automated a 1,676-item YouTube account cleanup with Python and YouTube Data API v3, preserving the nine newest likes through a tested deterministic split strategy.
- Reduced destructive-operation risk by implementing dry-run previews, explicit confirmation, bounded 180-item batches, and JSON audit reporting before production execution.
- Recovered a deleted cloud-agent deliverable from Git commit history, reorganized it as a standalone repository, and established secret-safe GitHub publishing controls.
- Diagnosed and resolved OAuth/API enablement separation and Windows Unicode failures, enabling reliable processing of multilingual YouTube metadata.
- Coordinated Cursor and Codex in a human-approved agent workflow that completed 102 production updates while stopping safely on permission/quota signals.

## LinkedIn

最近我完成了一個很實際、也很適合檢驗 AI 協作工程能力的專案：用 Python 與 YouTube Data API v3，整理累積多年的 1,676 部「喜歡的影片」，只保留最近九部。真正困難的不是逐筆呼叫 API，而是如何安全地修改真實帳號。我加入 dry-run、人工確認、批次上限、OAuth 機密隔離與 JSON 稽核報告，並處理 Google API 未啟用、Windows Unicode、影片失效及配額限制。專案由 Cursor 產生初版，Codex 負責從 Git 歷史復原、整合、測試、部署與實際執行；第一批成功完成 102 次更新並在風險訊號出現時自動停止。這次經驗再次證明，AI Agent 的價值不是取代人，而是讓人專注在授權、風險與架構決策。

## Commit message

```text
docs: publish project documentation and reusable content skill
```

## PR description

### Summary

Organize the YouTube cleanup repository and publish engineering and portfolio documentation.

### Changes

- add a comprehensive engineering README
- add a story-driven Medium draft and portfolio collateral
- add the reusable `publish-github-medium` Codex skill
- isolate OAuth credentials, tokens, and runtime reports
- configure UTF-8 console output on Windows

### Testing

- `python -m unittest discover -s tests -v`
- `python -m py_compile cleanup_liked.py`
- `git diff --check`
- secret and ignore verification

### Screenshots

Not applicable; this is a CLI project.

### Future Work

- persistent checkpoints and retry classification
- scheduled quota-aware continuation
- web approval UI and CI matrix

## Follow-on projects

1. **Version 2 – Resumable jobs:** SQLite checkpoints, error taxonomy, idempotent retries, and progress dashboards.
2. **AI-assisted review:** summarize videos selected for removal while retaining explicit human approval.
3. **Agent workflow:** a scheduled Codex task that checks quota, proposes the next batch, and waits for authorization.
4. **Web UI:** FastAPI backend with a visual keep/remove approval queue and OAuth callback flow.
5. **Delivery architecture:** Docker, CI across operating systems, secret scanning, release artifacts, and signed builds.
6. **Consulting template:** generalize the safety pattern into an auditable account-cleanup agent for other SaaS APIs.
