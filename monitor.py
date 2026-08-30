import json
import os
import requests

USERNAME = "MSNightmare"
STATE_FILE = "seen_repos.json"

webhook = os.environ["DISCORD_WEBHOOK"]


def get_repos():
    url = f"https://api.github.com/users/{USERNAME}/repos"

    response = requests.get(
        url,
        params={
            "type": "owner",
            "sort": "created",
            "direction": "desc",
            "per_page": 100
        },
        timeout=10
    )

    response.raise_for_status()
    return response.json()


def main():
    repos = get_repos()

    try:
        with open(STATE_FILE) as f:
            seen = set(json.load(f))
    except FileNotFoundError:
        seen = set()

    new_repos = [
        repo for repo in repos
        if repo["id"] not in seen and not repo["private"]
    ]

    for repo in new_repos:
        message = (
            f"<@1009365611740147802> 🔔 **New public repository!**\n"
            f"**{repo['full_name']}**\n"
            f"{repo['html_url']}"
        )

        response = requests.post(
            webhook,
            json={"content": message},
            timeout=10
        )
        response.raise_for_status()

        seen.add(repo["id"])

    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f)


if __name__ == "__main__":
    main()  
