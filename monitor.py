import json
import os
from datetime import datetime, timezone

import requests


USERNAME = "MSNightmare"
STATE_FILE = "seen_repos.json"
DISCORD_USER_ID = "1009365611740147802"

webhook = os.environ["DISCORD_WEBHOOK"]
github_token = os.environ["GITHUB_TOKEN"]


def get_repos():
    """Get all public repositories owned by the monitored user."""

    repos = []
    page = 1

    while True:
        response = requests.get(
            f"https://api.github.com/users/{USERNAME}/repos",
            params={
                "type": "owner",
                "sort": "created",
                "direction": "desc",
                "per_page": 100,
                "page": page,
            },
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {github_token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15,
        )

        response.raise_for_status()

        page_repos = response.json()

        if not page_repos:
            break

        repos.extend(
            repo for repo in page_repos
            if not repo["private"]
        )

        if len(page_repos) < 100:
            break

        page += 1

    return repos


def parse_github_time(value):
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def save_state(timestamp):
    with open(STATE_FILE, "w") as f:
        json.dump(
            {
                "last_checked": timestamp.isoformat()
            },
            f,
            indent=2,
        )


def main():
    check_started = datetime.now(timezone.utc)

    repos = get_repos()

    # Load existing state.
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)

    except (FileNotFoundError, json.JSONDecodeError):
        state = None

    # First run / migration from the old ID-list format

    if isinstance(state, list):
        print("Old repository state detected. Migrating...")

        old_ids = set(state)

        old_repos = [
            repo
            for repo in repos
            if repo["id"] in old_ids
        ]

        if old_repos:
            last_checked = max(
                parse_github_time(repo["created_at"])
                for repo in old_repos
            )

            print(
                f"Migrated state from {len(old_repos)} "
                f"previously known repositories."
            )

        else:
            newest_repo_time = max(
                (
                    parse_github_time(repo["created_at"])
                    for repo in repos
                ),
                default=check_started,
            )

            last_checked = newest_repo_time

            print(
                "Could not match old repository IDs. "
                "Initialising from newest repository."
            )

    elif isinstance(state, dict) and "last_checked" in state:
        last_checked = parse_github_time(
            state["last_checked"]
        )

    else:
        # Completely new installation.
        newest_repo_time = max(
            (
                parse_github_time(repo["created_at"])
                for repo in repos
            ),
            default=check_started,
        )

        save_state(newest_repo_time)

        print(
            "Initial repository timestamp saved. "
            "No notifications sent."
        )

        return

    # Detect repositories created since the last check

    new_repos = [
        repo
        for repo in repos
        if parse_github_time(repo["created_at"]) > last_checked
    ]

    new_repos.sort(
        key=lambda repo: parse_github_time(repo["created_at"])
    )

    print(f"Found {len(new_repos)} new public repositories.")

    # Send Discord notifications

    for repo in new_repos:
        message = (
            f"<@{DISCORD_USER_ID}> 🔔 **New public repository!**\n"
            f"**{repo['full_name']}**\n"
            f"{repo['html_url']}"
        )

        response = requests.post(
            webhook,
            json={"content": message},
            timeout=15,
        )

        response.raise_for_status()

        print(
            f"Notified Discord: {repo['full_name']}"
        )
        
    # Save state only after successful processing

    save_state(check_started)

    print(
        f"Repository timestamp updated to "
        f"{check_started.isoformat()}"
    )


if __name__ == "__main__":
    main()
