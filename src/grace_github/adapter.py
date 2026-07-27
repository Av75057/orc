import os
from typing import Optional


class GitHubAdapter:
    def __init__(self, token: Optional[str] = None):
        self._token = token or os.environ.get("GITHUB_TOKEN", "")

    def create_pr(self, config):
        print(f"[GitHub] PR creation not implemented in stub. Token: {'set' if self._token else 'not set'}")
        return {"url": "", "number": 0}
