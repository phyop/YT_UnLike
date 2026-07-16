# How I Cleaned 1,676 YouTube Likes with Python Without Trusting Automation Blindly

## The problem

My YouTube Liked videos playlist had quietly grown to 1,676 entries. I wanted a simple outcome: keep only the nine most recently liked videos and remove the rating from everything older.

The user interface was fine for a handful of videos, but not for more than a thousand. The obvious answer was automation. The dangerous part was that the operation was destructive and account-wide. A sorting bug, reversed playlist order, or accidental confirmation could remove the wrong ratings at scale.

So the real project was not "call an API in a loop." It was to build a workflow that could prove what it intended to change before receiving permission to change anything.

## Why this was harder than expected

YouTube Data API v3 exposes the authenticated user's liked-video playlist and lets an application update a video rating. That sounds straightforward, but several systems have to agree:

- Google Cloud must have YouTube Data API v3 enabled.
- The OAuth client must be configured as a Desktop application.
- The user must grant the correct YouTube scope.
- The liked playlist must be read in the intended order.
- API quota and per-item failures must be handled safely.
- OAuth credentials and tokens must never enter Git history.

The project also crossed multiple environments. Cursor created the first implementation in a cloud workflow, while the actual OAuth login and account mutation had to run on my Windows computer. Codex then recovered, organized, validated, and executed the local project with human approval at each destructive boundary.

## Debugging the workflow

### 1. Recovering the implementation

The first surprise was operational rather than technical: I could not find a ZIP artifact to move. The useful source was already stored in Git history. Recovering the committed files was more reliable than depending on an ephemeral cloud download.

This reinforced a simple engineering rule: a deliverable is not durable until it is in version control and can be reproduced from a known commit.

### 2. Separating OAuth setup from API enablement

Placing `client_secret.json` in the project directory was necessary, but not sufficient. OAuth identity and API availability are separate controls. The login flow can succeed while API calls still fail if YouTube Data API v3 is disabled for the Google Cloud project.

The final setup checklist treated them independently:

1. Enable YouTube Data API v3.
2. Create a Desktop OAuth client.
3. Download `client_secret.json` locally.
4. Authorize the requested YouTube scope.
5. Store the resulting token locally and keep both files out of Git.

### 3. Making the default behavior non-destructive

The command defaults to dry-run mode. It retrieves the complete liked-video list, preserves the newest N items, and prints the planned removals without changing the account.

```powershell
python cleanup_liked.py --keep 9
```

Only an explicit execution flag permits mutation:

```powershell
python cleanup_liked.py --keep 9 --execute
```

This separation mattered more than any single API call. The preview gave me a chance to verify that the nine retained videos matched what I saw in YouTube before authorizing removal.

### 4. Handling Windows Unicode output

Video titles can contain characters and emoji that are not representable in the legacy Windows CP950 console encoding. That produced `UnicodeEncodeError` failures during reporting, even though the API data itself was valid.

The solution was to make console output UTF-8 aware and provide a replacement fallback. In practice, Unicode handling is part of production correctness whenever external metadata is printed to a terminal.

### 5. Respecting quotas and partial failures

Removing a rating requires a write request for each video, so a large cleanup cannot assume unlimited daily quota. The tool supports bounded batches:

```powershell
python cleanup_liked.py --keep 9 --execute --max-unlike 180
```

During the production run, the workflow completed 102 updates before stopping safely when API responses indicated that continuing was not appropriate. A batch limit, audit report, and idempotent selection rule made continuation manageable instead of turning partial completion into a recovery incident.

## The final design

The workflow is deliberately simple:

1. Authenticate locally with OAuth.
2. Resolve the authenticated user's liked-video playlist.
3. Retrieve items in playlist order.
4. Split the list into "keep" and "planned removal" groups.
5. Show a dry-run preview and write an audit report.
6. Require explicit execution approval.
7. Process a bounded batch and record every outcome.
8. Stop safely on quota, permission, or unavailable-video signals.

The key architectural choice is the boundary between planning and execution. Dry-run and execute use the same deterministic selection logic. The second phase does not independently decide what should be removed; it applies a plan that the user has already reviewed.

## What I learned

Destructive automation needs more than correct code. It needs a safety model. Defaults should be reversible or read-only, scope should be visible, execution should require explicit intent, and results should be auditable.

I also learned that AI-assisted development works best as a controlled pipeline. Cursor accelerated initial implementation. Codex handled local recovery, repository hygiene, validation, and execution support. Git supplied the durable handoff. Human approval remained the authority for OAuth access and account changes.

Finally, operational details are part of the architecture. OAuth configuration, API enablement, Windows encoding, quota limits, and Git ignore rules were not peripheral setup issues. Any one of them could determine whether the system was safe and usable.

## Pitfalls to avoid

- Never commit `client_secret.json`, `token.json`, or execution reports containing account data.
- Never make destructive mode the default.
- Never assume OAuth success means the target API is enabled.
- Never assume external titles are compatible with the local console encoding.
- Never process thousands of write requests without quotas, batch limits, and checkpoints.
- Never let an AI agent move from preview to production without explicit human approval.

## Conclusion

The most valuable outcome was not removing old likes; it was building an automation workflow that earned permission to act by showing its plan first.
