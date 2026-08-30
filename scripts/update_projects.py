"""
Fetches the latest public repositories for a GitHub user and writes them
into README.md between the LATEST-PROJECTS markers.

Runs inside GitHub Actions, where GITHUB_TOKEN is provided automatically.
"""

import os
import re
import requests

USERNAME = "Shubhambilgi"
README_PATH = "README.md"
MAX_REPOS = 6  # how many recent repos to show

# Repos already featured with hand-written descriptions above —
# skip these here so they don't get duplicated.
FEATURED_REPOS = {
    "camera-segmentation-av",
    "AgriCast-Data",
    "LaptopMatch-Recommendation-Dashboard",
    "BreachAware-LAW",
    "web-App-Pen-testing",
    "CyberVault_CTF",
}

LANGUAGE_COLORS = {
    "Python": "3776AB",
    "TypeScript": "3178C6",
    "JavaScript": "F7DF1E",
    "HTML": "E34F26",
    "CSS": "1572B6",
    "Java": "ED8B00",
    "Jupyter Notebook": "F37626",
}


def fetch_repos():
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"https://api.github.com/users/{USERNAME}/repos"
    params = {"sort": "updated", "direction": "desc", "per_page": 100}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def build_markdown(repos):
    lines = []
    count = 0
    for repo in repos:
        if repo.get("fork"):
            continue
        if repo.get("archived"):
            continue
        name = repo["name"]
        if name == USERNAME or name in FEATURED_REPOS:
            continue

        count += 1
        if count > MAX_REPOS:
            break

        description = repo.get("description") or "No description yet."
        language = repo.get("language")
        stars = repo.get("stargazers_count", 0)
        forks = repo.get("forks_count", 0)
        html_url = repo["html_url"]

        lang_badge = ""
        if language:
            color = LANGUAGE_COLORS.get(language, "808080")
            lang_badge = f"![{language}](https://img.shields.io/badge/{language.replace(' ', '%20')}-{color}?style=flat-square) "

        lines.append(f"**[{name}]({html_url})**")
        lines.append(f"{description}")
        lines.append(
            f"{lang_badge}![Stars](https://img.shields.io/badge/★-{stars}-f59e0b?style=flat-square) "
            f"![Forks](https://img.shields.io/badge/⑂-{forks}-7c3aed?style=flat-square)"
        )
        lines.append("")

    if count == 0:
        lines.append("_No additional repositories yet — check back soon._")

    return "\n".join(lines)


def update_readme(new_content):
    with open(README_PATH, "r", encoding="utf-8") as f:
        readme = f.read()

    pattern = re.compile(
        r"(<!-- LATEST-PROJECTS:START -->)(.*?)(<!-- LATEST-PROJECTS:END -->)",
        re.DOTALL,
    )
    replacement = f"\\1\n{new_content}\n\\3"
    updated = pattern.sub(replacement, readme)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)


if __name__ == "__main__":
    repos = fetch_repos()
    markdown = build_markdown(repos)
    update_readme(markdown)
    print("README.md updated with latest repositories.")
