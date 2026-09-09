"""
Automatically updates the GitHub profile README.

Features:
1. Calculates GitHub language usage.
2. Selects 2 projects every day.
3. Displays all public repositories.
4. Updates README.md automatically.
5. Uses GitHub Actions GITHUB_TOKEN.
"""

import os
import re
from datetime import date
from urllib.parse import quote

import requests


# ============================================================
# CONFIGURATION
# ============================================================

USERNAME = "Shubhambilgi"
README_PATH = "README.md"

API_URL = "https://api.github.com"

FEATURED_COUNT = 2

# Repositories that should not appear in the daily featured section.
EXCLUDED_FROM_FEATURED = {
    USERNAME.lower(),
}

# Languages that we want to recognize with custom colors.
LANGUAGE_COLORS = {
    "Python": "3776AB",
    "TypeScript": "3178C6",
    "JavaScript": "F7DF1E",
    "C++": "00599C",
    "C": "A8B9CC",
    "Java": "ED8B00",
    "HTML": "E34F26",
    "CSS": "1572B6",
    "SQL": "4479A1",
    "Jupyter Notebook": "F37626",
    "Shell": "89E051",
    "PHP": "777BB4",
    "Go": "00ADD8",
    "Rust": "DEA584",
}


# ============================================================
# GITHUB SESSION
# ============================================================

def create_session():
    """
    Creates a requests session.

    The GitHub Actions token is used when available.
    """

    token = os.environ.get("GITHUB_TOKEN", "")

    session = requests.Session()

    session.headers.update({
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })

    if token:
        session.headers.update({
            "Authorization": f"Bearer {token}"
        })

    return session


session = create_session()


# ============================================================
# FETCH REPOSITORIES
# ============================================================

def fetch_repos():
    """
    Fetch all public repositories owned by the user.

    GitHub API returns a maximum of 100 repositories per request,
    so pagination is used.
    """

    repos = []

    page = 1

    while True:

        url = f"{API_URL}/users/{USERNAME}/repos"

        params = {
            "sort": "updated",
            "direction": "desc",
            "per_page": 100,
            "page": page,
        }

        response = session.get(
            url,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        batch = response.json()

        if not batch:
            break

        for repo in batch:

            # Do not include repositories owned by somebody else.
            if repo.get("owner", {}).get("login", "").lower() != USERNAME.lower():
                continue

            # Skip forks.
            if repo.get("fork"):
                continue

            repos.append(repo)

        if len(batch) < 100:
            break

        page += 1

    return repos


# ============================================================
# FETCH LANGUAGE DATA
# ============================================================

def fetch_repo_languages(repo):
    """
    Fetches the amount of code written in each language
    for one repository.

    GitHub returns language usage as bytes.
    """

    languages_url = repo.get("languages_url")

    if not languages_url:
        return {}

    response = session.get(
        languages_url,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def calculate_language_stats(repos):
    """
    Combines language data from all repositories.
    """

    totals = {}

    for repo in repos:

        # Archived repositories are ignored from language statistics.
        if repo.get("archived"):
            continue

        try:
            languages = fetch_repo_languages(repo)
        except requests.RequestException as error:
            print(
                f"Could not fetch languages for "
                f"{repo.get('name')}: {error}"
            )
            continue

        for language, bytes_count in languages.items():

            totals[language] = (
                totals.get(language, 0) + bytes_count
            )

    return totals


# ============================================================
# LANGUAGE MARKDOWN
# ============================================================

def build_language_markdown(language_totals):
    """
    Creates a language distribution section.
    """

    if not language_totals:
        return "_No language data available yet._"

    total_bytes = sum(language_totals.values())

    if total_bytes == 0:
        return "_No language data available yet._"

    sorted_languages = sorted(
        language_totals.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    # Show top 10 languages.
    sorted_languages = sorted_languages[:10]

    lines = []

    lines.append(
        "<p align=\"center\">"
    )

    for language, bytes_count in sorted_languages:

        percentage = (
            bytes_count / total_bytes
        ) * 100

        percentage_text = f"{percentage:.1f}%"

        color = LANGUAGE_COLORS.get(
            language,
            "808080",
        )

        badge_language = quote(
            language.replace(" ", "_")
        )

        badge = (
            f"https://img.shields.io/badge/"
            f"{badge_language}-"
            f"{percentage_text}-"
            f"{color}"
            f"?style=for-the-badge"
        )

        lines.append(
            f'  <img src="{badge}" alt="{language}" />'
        )

    lines.append("</p>")

    lines.append("")
    lines.append(
        "> Language percentages are based on code bytes "
        "reported by GitHub across my repositories."
    )

    return "\n".join(lines)


# ============================================================
# DAILY PROJECT SELECTION
# ============================================================

def select_daily_projects(repos):
    """
    Selects 2 repositories based on today's date.

    The same projects remain visible throughout the day.
    Tomorrow the selection automatically changes.
    """

    candidates = []

    for repo in repos:

        name = repo.get("name", "")

        if name.lower() in EXCLUDED_FROM_FEATURED:
            continue

        if repo.get("fork"):
            continue

        if repo.get("archived"):
            continue

        candidates.append(repo)

    if not candidates:
        return []

    # Sort by recently updated repositories first.
    candidates.sort(
        key=lambda repo: repo.get(
            "updated_at",
            ""
        ),
        reverse=True,
    )

    today_number = date.today().toordinal()

    selected = []

    total_candidates = len(candidates)

    for index in range(
        min(FEATURED_COUNT, total_candidates)
    ):

        position = (
            today_number * FEATURED_COUNT + index
        ) % total_candidates

        selected.append(
            candidates[position]
        )

    return selected


# ============================================================
# PROJECT MARKDOWN
# ============================================================

def build_project_card(repo):
    """
    Builds one featured project card.
    """

    name = repo.get("name", "Unknown Repository")

    description = (
        repo.get("description")
        or "No description provided yet."
    )

    language = (
        repo.get("language")
        or "Multiple"
    )

    stars = repo.get(
        "stargazers_count",
        0,
    )

    forks = repo.get(
        "forks_count",
        0,
    )

    url = repo.get(
        "html_url",
        "#",
    )

    language_color = LANGUAGE_COLORS.get(
        language,
        "808080",
    )

    language_badge = (
        f"https://img.shields.io/badge/"
        f"{quote(language.replace(' ', '_'))}-"
        f"{language_color}"
        f"?style=flat-square"
    )

    lines = []

    lines.append(
        f'### 🚀 [{name}]({url})'
    )

    lines.append("")
    lines.append(description)
    lines.append("")

    lines.append(
        f'![{language}]({language_badge}) '
        f'![Stars](https://img.shields.io/badge/'
        f'⭐%20Stars-{stars}-f59e0b?style=flat-square) '
        f'![Forks](https://img.shields.io/badge/'
        f'🍴%20Forks-{forks}-7c3aed?style=flat-square)'
    )

    lines.append("")

    return "\n".join(lines)


def build_featured_markdown(repos):
    """
    Builds the daily featured projects section.
    """

    if not repos:
        return "_No projects available._"

    today = date.today().strftime(
        "%d %B %Y"
    )

    lines = []

    lines.append(
        f"**Automatically selected for {today}**"
    )

    lines.append("")

    for repo in repos:
        lines.append(
            build_project_card(repo)
        )

    return "\n".join(lines)


# ============================================================
# ALL REPOSITORIES
# ============================================================

def build_all_repositories_markdown(repos):
    """
    Builds a compact table containing all repositories.
    """

    if not repos:
        return "_No repositories found._"

    # Sort newest updated repositories first.
    repos = sorted(
        repos,
        key=lambda repo: repo.get(
            "updated_at",
            ""
        ),
        reverse=True,
    )

    lines = []

    lines.append(
        "| Repository | Language | ⭐ Stars | 🍴 Forks | Status |"
    )

    lines.append(
        "|---|---|---:|---:|---|"
    )

    for repo in repos:

        name = repo.get(
            "name",
            "Unknown",
        )

        url = repo.get(
            "html_url",
            "#",
        )

        language = (
            repo.get("language")
            or "—"
        )

        stars = repo.get(
            "stargazers_count",
            0,
        )

        forks = repo.get(
            "forks_count",
            0,
        )

        if repo.get("archived"):
            status = "📦 Archived"
        else:
            status = "🟢 Active"

        lines.append(
            f"| [{name}]({url}) | "
            f"{language} | "
            f"{stars} | "
            f"{forks} | "
            f"{status} |"
        )

    return "\n".join(lines)


# ============================================================
# README UPDATE FUNCTION
# ============================================================

def replace_section(
    readme,
    start_marker,
    end_marker,
    new_content,
):
    """
    Replaces content between two README markers.
    """

    pattern = re.compile(
        rf"({re.escape(start_marker)}).*?"
        rf"({re.escape(end_marker)})",
        re.DOTALL,
    )

    replacement = (
        f"{start_marker}\n"
        f"{new_content}\n"
        f"{end_marker}"
    )

    updated_readme, replacements = pattern.subn(
        replacement,
        readme,
        count=1,
    )

    if replacements == 0:
        print(
            f"Warning: markers not found: "
            f"{start_marker}"
        )

    return updated_readme


def update_readme(
    language_markdown,
    featured_markdown,
    repositories_markdown,
):
    """
    Updates all automatically generated README sections.
    """

    with open(
        README_PATH,
        "r",
        encoding="utf-8",
    ) as file:

        readme = file.read()

    # Language statistics.
    readme = replace_section(
        readme,
        "<!-- LANGUAGE-STATS:START -->",
        "<!-- LANGUAGE-STATS:END -->",
        language_markdown,
    )

    # Daily projects.
    readme = replace_section(
        readme,
        "<!-- FEATURED-PROJECTS:START -->",
        "<!-- FEATURED-PROJECTS:END -->",
        featured_markdown,
    )

    # All repositories.
    readme = replace_section(
        readme,
        "<!-- ALL-REPOSITORIES:START -->",
        "<!-- ALL-REPOSITORIES:END -->",
        repositories_markdown,
    )

    # Last updated date.
    last_updated = (
        f"Last automatically updated: "
        f"{date.today().strftime('%d %B %Y')}"
    )

    readme = replace_section(
        readme,
        "<!-- PROFILE-LAST-UPDATED:START -->",
        "<!-- PROFILE-LAST-UPDATED:END -->",
        last_updated,
    )

    with open(
        README_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        file.write(readme)


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        f"Fetching repositories for @{USERNAME}..."
    )

    repos = fetch_repos()

    print(
        f"Found {len(repos)} repositories."
    )

    # --------------------------------------------------------
    # Language statistics
    # --------------------------------------------------------

    print(
        "Calculating language statistics..."
    )

    language_totals = (
        calculate_language_stats(repos)
    )

    language_markdown = (
        build_language_markdown(
            language_totals
        )
    )

    # --------------------------------------------------------
    # Daily projects
    # --------------------------------------------------------

    print(
        "Selecting today's featured projects..."
    )

    daily_projects = (
        select_daily_projects(repos)
    )

    featured_markdown = (
        build_featured_markdown(
            daily_projects
        )
    )

    # --------------------------------------------------------
    # All repositories
    # --------------------------------------------------------

    print(
        "Building repository list..."
    )

    repositories_markdown = (
        build_all_repositories_markdown(
            repos
        )
    )

    # --------------------------------------------------------
    # Update README
    # --------------------------------------------------------

    print(
        "Updating README.md..."
    )

    update_readme(
        language_markdown,
        featured_markdown,
        repositories_markdown,
    )

    print(
        "README.md successfully updated."
    )


if __name__ == "__main__":
    main()
