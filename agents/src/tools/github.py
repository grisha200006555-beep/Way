import httpx

from ..config import settings
from .registry import tool


GH_API = "https://api.github.com"


def _headers() -> dict:
    if not settings.github_token:
        raise RuntimeError("GITHUB_TOKEN not configured")
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


@tool(
    name="github_list_issues",
    description="List open issues in a repo. Returns up to 20 issues with number, title, author.",
    input_schema={
        "type": "object",
        "properties": {
            "repo": {"type": "string", "description": "owner/repo, e.g. octocat/hello-world"},
        },
        "required": ["repo"],
    },
)
async def github_list_issues(repo: str) -> str:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{GH_API}/repos/{repo}/issues",
                        headers=_headers(),
                        params={"state": "open", "per_page": 20})
    if r.status_code >= 400:
        return f"ERROR {r.status_code}: {r.text[:500]}"
    issues = r.json()
    if not issues:
        return "No open issues."
    return "\n".join(
        f"#{i['number']} [{i.get('user', {}).get('login', '?')}] {i['title']}"
        for i in issues if "pull_request" not in i
    )


@tool(
    name="github_get_issue",
    description="Fetch full body and recent comments of an issue or PR.",
    input_schema={
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "number": {"type": "integer"},
        },
        "required": ["repo", "number"],
    },
)
async def github_get_issue(repo: str, number: int) -> str:
    async with httpx.AsyncClient(timeout=15) as c:
        issue = await c.get(f"{GH_API}/repos/{repo}/issues/{number}", headers=_headers())
        comments = await c.get(f"{GH_API}/repos/{repo}/issues/{number}/comments", headers=_headers())
    if issue.status_code >= 400:
        return f"ERROR {issue.status_code}: {issue.text[:500]}"
    i = issue.json()
    out = [f"#{i['number']} {i['title']}", f"by {i['user']['login']}", "", i.get("body") or "(empty)"]
    for c in comments.json()[-5:]:
        out += ["---", f"{c['user']['login']}:", c.get("body") or ""]
    return "\n".join(out)
