---
name: publish-github-medium
description: Organize a software project and create distinct engineering-facing GitHub documentation and story-driven Medium content, then publish both safely. Use when Codex is asked to clean a project root, improve or publish a GitHub repository, write or publish a Medium technical article, create portfolio collateral, or perform the combined GitHub-and-Medium publishing workflow.
---

# Publish GitHub and Medium

Run this workflow end to end unless the user limits the scope.

## 1. Audit and protect

- Inspect repository instructions, status, tracked files, remotes, tests, and generated artifacts.
- Never expose or commit credentials, OAuth files, tokens, private reports, personal data, or environment files.
- Add secret and runtime paths to `.gitignore` before moving or staging files.
- Preserve unrelated user changes. Confirm scope if the worktree is mixed.

## 2. Organize the repository

- Keep only common entry files at root: README, license, dependency manifests, entry point, and repository configuration.
- Put long-form content in `docs/`, runtime output in `runtime/`, tests in `tests/`, and reusable local skills in `skills/`.
- Update code defaults, documentation, and tests when moving files.
- Prefer a minimal structure appropriate to the project; do not create empty folders.

## 3. Create portfolio content

Read [content-requirements.md](references/content-requirements.md) and produce every relevant deliverable.

- Write README for engineers, interviewers, and contributors.
- Write the Medium article as an original chronological story, not a README paraphrase.
- Ground all claims, commands, architecture, test results, and lessons in repository evidence.
- Describe AI collaboration honestly; do not claim fully autonomous behavior when human approval was required.

## 4. Validate

- Run the most relevant unit tests, syntax checks, secret checks, and `git diff --check`.
- Confirm ignored secrets with `git check-ignore` and ensure `git status` contains only intended files.
- Do not publish if credentials or tokens are staged.

## 5. Publish GitHub

- Follow the installed GitHub publishing workflow.
- Use a Conventional Commit message.
- Commit only intended files, push the branch, and create a draft PR when working on a non-default publishing branch.
- If the user explicitly requests direct publication and the repository already uses direct-to-main, push the validated commit to its configured branch.
- Return repository, commit, branch, validation, and PR links as applicable.

## 6. Publish Medium

- Use the browser surface selected for `https://medium.com/` and the user's existing signed-in session.
- Create a new story from the prepared Medium Markdown.
- Preserve heading hierarchy, code blocks, lists, and links. Add up to five relevant tags.
- Treat the final Publish action as an external side effect. If the user already explicitly asked to publish Medium, proceed; otherwise request confirmation immediately before publishing.
- Verify the public story URL after publication. If authentication blocks publication, leave the story ready and ask the user to sign in.

## 7. Hand off

- Report the GitHub and Medium URLs, files created, checks run, and any remaining manual work.
- Include the reusable invocation: `Use $publish-github-medium to organize and publish <project path> to GitHub and Medium.`
