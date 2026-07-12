#!/usr/bin/env python3
"""清理 YouTube「喜歡的影片」：只保留最近 N 部，其餘取消喜歡。

預設為 dry-run（只預覽、不寫入）。加上 --execute 才會真正取消喜歡。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 需要能讀取喜歡清單並變更評分
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

DEFAULT_KEEP = 9
# videos.rate 每次約 50 quota；預設日額 10,000 ≈ 每天最多約 200 次
DEFAULT_SLEEP_SECONDS = 0.2
SCRIPT_DIR = Path(__file__).resolve().parent
PRIVATE_DIR = SCRIPT_DIR / "config" / "private"
RUNTIME_DIR = SCRIPT_DIR / "runtime"


@dataclass(frozen=True)
class LikedVideo:
    video_id: str
    title: str
    channel_title: str
    liked_at: str | None
    position: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="只保留最近 N 部 YouTube 喜歡影片，其餘取消喜歡。",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=DEFAULT_KEEP,
        help=f"要保留的最近喜歡影片數量（預設 {DEFAULT_KEEP}）",
    )
    parser.add_argument(
        "--credentials",
        type=Path,
        default=PRIVATE_DIR / "client_secret.json",
        help="Google OAuth Desktop 應用程式 client_secret.json 路徑",
    )
    parser.add_argument(
        "--token",
        type=Path,
        default=PRIVATE_DIR / "token.json",
        help="OAuth token 快取路徑（會自動建立／更新）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="真正執行取消喜歡（未加此參數時僅預覽）",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="略過互動確認（僅在搭配 --execute 時有效）",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=DEFAULT_SLEEP_SECONDS,
        help=f"每次取消喜歡之間的延遲秒數（預設 {DEFAULT_SLEEP_SECONDS}）",
    )
    parser.add_argument(
        "--max-unlike",
        type=int,
        default=0,
        help="本次最多取消幾部（0=不限制；可用來避開日配額）",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=RUNTIME_DIR / "last_run_report.json",
        help="執行結果報告輸出路徑",
    )
    return parser.parse_args(argv)


def split_keep_and_unlike(
    videos: list[LikedVideo],
    keep: int,
) -> tuple[list[LikedVideo], list[LikedVideo]]:
    if keep < 0:
        raise ValueError("keep 必須 >= 0")
    return videos[:keep], videos[keep:]


def get_credentials(credentials_path: Path, token_path: Path) -> Credentials:
    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not credentials_path.exists():
            raise FileNotFoundError(
                f"找不到 OAuth 憑證檔：{credentials_path}\n"
                "請依 README 在 Google Cloud Console 建立 Desktop OAuth 用戶端，"
                "下載 JSON 後放到該路徑。"
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        # 會開啟瀏覽器讓你登入 YouTube 帳號並授權
        creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def build_youtube(creds: Credentials) -> Any:
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def get_likes_playlist_id(youtube: Any) -> str:
    response = (
        youtube.channels()
        .list(mine=True, part="contentDetails")
        .execute()
    )
    items = response.get("items") or []
    if not items:
        raise RuntimeError("無法取得頻道資訊，請確認已登入正確的 Google 帳號。")
    likes_id = (
        items[0]
        .get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("likes")
    )
    if not likes_id:
        raise RuntimeError("此帳號沒有「喜歡的影片」播放清單 ID。")
    return likes_id


def list_liked_videos(youtube: Any, playlist_id: str) -> list[LikedVideo]:
    """依「喜歡的影片」播放清單順序取得全部項目（通常最新喜歡在最前）。"""
    videos: list[LikedVideo] = []
    page_token: str | None = None
    position = 0

    while True:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=page_token,
        )
        response = request.execute()
        for item in response.get("items") or []:
            snippet = item.get("snippet") or {}
            content = item.get("contentDetails") or {}
            video_id = content.get("videoId") or snippet.get("resourceId", {}).get(
                "videoId"
            )
            if not video_id:
                continue
            videos.append(
                LikedVideo(
                    video_id=video_id,
                    title=snippet.get("title") or "(無標題)",
                    channel_title=snippet.get("videoOwnerChannelTitle")
                    or snippet.get("channelTitle")
                    or "(未知頻道)",
                    # playlistItems.snippet.publishedAt = 加入「喜歡」清單的時間
                    liked_at=snippet.get("publishedAt")
                    or content.get("videoPublishedAt"),
                    position=position,
                )
            )
            position += 1

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return videos


def unlike_video(youtube: Any, video_id: str) -> None:
    youtube.videos().rate(id=video_id, rating="none").execute()


def print_video_list(label: str, videos: list[LikedVideo], limit: int = 20) -> None:
    print(f"\n=== {label}（共 {len(videos)} 部）===")
    for video in videos[:limit]:
        print(
            f"  [{video.position + 1:4d}] {video.video_id}  "
            f"{video.title}  — {video.channel_title}"
        )
    if len(videos) > limit:
        print(f"  ... 還有 {len(videos) - limit} 部未列出")


def confirm_execute(to_unlike_count: int) -> bool:
    answer = input(
        f"\n即將取消喜歡 {to_unlike_count} 部影片。輸入 YES 確認："
    ).strip()
    return answer == "YES"


def write_report(
    path: Path,
    *,
    keep: list[LikedVideo],
    planned_unlike: list[LikedVideo],
    unliked: list[LikedVideo],
    failed: list[dict[str, str]],
    dry_run: bool,
) -> None:
    payload = {
        "dry_run": dry_run,
        "kept": [asdict(v) for v in keep],
        "planned_unlike_count": len(planned_unlike),
        "unliked_count": len(unliked),
        "unliked": [asdict(v) for v in unliked],
        "failed": failed,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args(argv)
    if args.keep < 0:
        print("錯誤：--keep 必須 >= 0", file=sys.stderr)
        return 2

    try:
        creds = get_credentials(args.credentials, args.token)
        youtube = build_youtube(creds)
        playlist_id = get_likes_playlist_id(youtube)
        print(f"喜歡的影片播放清單 ID：{playlist_id}")
        print("正在擷取全部喜歡影片（可能需要一點時間）...")
        liked = list_liked_videos(youtube, playlist_id)
    except FileNotFoundError as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 1
    except HttpError as exc:
        print(f"YouTube API 錯誤：{exc}", file=sys.stderr)
        return 1

    print(f"目前喜歡影片總數：{len(liked)}")
    keep, to_unlike = split_keep_and_unlike(liked, args.keep)

    if args.max_unlike > 0:
        to_unlike = to_unlike[: args.max_unlike]

    print_video_list(f"將保留（最近 {args.keep} 部）", keep, limit=max(args.keep, 9))
    print_video_list("將取消喜歡", to_unlike, limit=30)

    if not to_unlike:
        print("\n沒有需要取消喜歡的影片。")
        write_report(
            args.report,
            keep=keep,
            planned_unlike=[],
            unliked=[],
            failed=[],
            dry_run=not args.execute,
        )
        return 0

    if not args.execute:
        print(
            "\n[Dry-run] 尚未實際取消喜歡。"
            "確認清單無誤後，加上 --execute 再跑一次。"
        )
        write_report(
            args.report,
            keep=keep,
            planned_unlike=to_unlike,
            unliked=[],
            failed=[],
            dry_run=True,
        )
        print(f"報告已寫入：{args.report}")
        return 0

    if not args.yes and not confirm_execute(len(to_unlike)):
        print("已取消。")
        return 1

    unliked: list[LikedVideo] = []
    failed: list[dict[str, str]] = []

    for index, video in enumerate(to_unlike, start=1):
        try:
            unlike_video(youtube, video.video_id)
            unliked.append(video)
            print(
                f"[{index}/{len(to_unlike)}] 已取消喜歡：{video.title} ({video.video_id})"
            )
        except HttpError as exc:
            reason = getattr(exc, "error_details", None) or str(exc)
            failed.append({"video_id": video.video_id, "error": str(reason)})
            print(
                f"[{index}/{len(to_unlike)}] 失敗：{video.video_id} — {exc}",
                file=sys.stderr,
            )
            # 配額用盡時提早結束，方便隔日用 --max-unlike 續跑
            if exc.resp is not None and exc.resp.status in {403, 429}:
                print(
                    "疑似配額／速率限制，停止後續請求。"
                    "可隔日再執行；已取消的不會重複處理。",
                    file=sys.stderr,
                )
                break
        if args.sleep > 0:
            time.sleep(args.sleep)

    write_report(
        args.report,
        keep=keep,
        planned_unlike=to_unlike,
        unliked=unliked,
        failed=failed,
        dry_run=False,
    )
    print(
        f"\n完成：成功取消 {len(unliked)} 部，失敗 {len(failed)} 部。"
        f"報告：{args.report}"
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
