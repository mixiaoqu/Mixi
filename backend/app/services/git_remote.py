from __future__ import annotations

import base64
import hashlib
import ipaddress
import os
import socket
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urlparse

from cryptography.fernet import Fernet

from app.core.config import settings

GIT_OUTPUT_ENCODING = "utf-8"
MAX_PATCH_CHARS_PER_COMMIT = 4_000
MAX_PATCH_CHARS_TOTAL = 18_000


class GitConnectionError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class GitRemoteInfo:
    repository_name: str
    branches: list[str]
    default_branch: str


@dataclass(frozen=True, slots=True)
class GitCommit:
    sha: str
    author_name: str
    author_email: str
    authored_at: datetime
    subject: str
    changed_files: list[str] = field(default_factory=list)
    patch: str = ""


def _fernet() -> Fernet:
    digest = hashlib.sha256(f"git-data-source:{settings.jwt_secret}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_credential(value: str | None) -> str | None:
    return _fernet().encrypt(value.encode()).decode() if value else None


def decrypt_credential(value: str | None) -> str | None:
    return _fernet().decrypt(value.encode()).decode() if value else None


def _repository_host(repository_url: str) -> str:
    parsed = urlparse(repository_url)
    if parsed.scheme not in {"http", "https", "ssh"} or not parsed.hostname:
        raise GitConnectionError("仅支持 HTTP、HTTPS 或 SSH 仓库地址")
    if parsed.username and parsed.scheme in {"http", "https"}:
        raise GitConnectionError("请不要在仓库地址中写入用户名或凭证")
    return parsed.hostname


def _validate_public_host(host: str) -> None:
    try:
        addresses = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise GitConnectionError("无法解析仓库服务器地址") from exc

    proxy_network = ipaddress.ip_network("198.18.0.0/15")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global and ip not in proxy_network:
            raise GitConnectionError("仓库地址不能指向本机或私有网络")


def _repository_name(repository_url: str) -> str:
    name = Path(urlparse(repository_url).path).name
    return name.removesuffix(".git") or "Git 仓库"


def _askpass_script(directory: Path) -> Path:
    if os.name == "nt":
        path = directory / "askpass.cmd"
        path.write_text(
            "@echo off\r\necho %~1 | findstr /I Username >nul\r\n"
            "if %errorlevel%==0 (echo oauth2) else (echo %GIT_DATA_SOURCE_TOKEN%)\r\n",
            encoding="utf-8",
        )
    else:
        path = directory / "askpass.sh"
        path.write_text(
            "#!/bin/sh\ncase \"$1\" in *Username*) echo oauth2 ;; *) echo \"$GIT_DATA_SOURCE_TOKEN\" ;; esac\n",
            encoding="utf-8",
        )
        path.chmod(0o700)
    return path


@contextmanager
def git_auth_environment(auth_type: str, credential: str | None) -> Iterator[dict[str, str]]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    with tempfile.TemporaryDirectory(prefix="agent-platform-git-auth-") as temp_dir:
        temp_path = Path(temp_dir)
        if auth_type == "token":
            askpass = _askpass_script(temp_path)
            env["GIT_ASKPASS"] = str(askpass)
            env["GIT_DATA_SOURCE_TOKEN"] = credential or ""
        elif auth_type == "ssh":
            key_path = temp_path / "identity"
            key_path.write_text(credential or "", encoding="utf-8")
            key_path.chmod(0o600)
            known_hosts = temp_path / "known_hosts"
            env["GIT_SSH_COMMAND"] = (
                f'ssh -i "{key_path}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new '
                f'-o UserKnownHostsFile="{known_hosts}"'
            )
        yield env


def _run_git(args: list[str], *, env: dict[str, str], timeout: int, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            check=False,
            cwd=cwd,
            env=env,
            text=True,
            encoding=GIT_OUTPUT_ENCODING,
            errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise GitConnectionError("服务器未安装 Git") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitConnectionError("读取仓库超时") from exc
    if result.returncode != 0:
        raise GitConnectionError("无法读取仓库，请检查地址、分支和凭证")
    return result.stdout or ""


def _truncate_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}\n...（内容过长，已截断）"


def _changed_files_for_commit(sha: str, *, repository_path: Path, env: dict[str, str]) -> list[str]:
    output = _run_git(
        ["show", "--format=", "--name-only", "--no-renames", sha],
        cwd=repository_path,
        env=env,
        timeout=20,
    )
    return [line.strip() for line in output.splitlines() if line.strip()]


def _patch_for_commit(
    sha: str,
    *,
    repository_path: Path,
    env: dict[str, str],
    remaining_budget: int,
) -> str:
    if remaining_budget <= 0:
        return ""
    output = _run_git(
        ["show", "--format=", "--find-renames", "--unified=3", "--no-ext-diff", sha],
        cwd=repository_path,
        env=env,
        timeout=30,
    )
    return _truncate_text(output, min(MAX_PATCH_CHARS_PER_COMMIT, remaining_budget))


def inspect_remote(repository_url: str, auth_type: str, credential: str | None) -> GitRemoteInfo:
    url = repository_url.strip()
    host = _repository_host(url)
    _validate_public_host(host)
    with git_auth_environment(auth_type, credential) as env:
        output = _run_git(["ls-remote", "--symref", url, "HEAD", "refs/heads/*"], env=env, timeout=20)

    branches: list[str] = []
    default_branch = ""
    for line in output.splitlines():
        if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD"):
            default_branch = line.removeprefix("ref: refs/heads/").removesuffix("\tHEAD")
        elif "\trefs/heads/" in line:
            branch = line.split("\trefs/heads/", 1)[1]
            if branch not in branches:
                branches.append(branch)

    branches.sort()
    if not branches:
        raise GitConnectionError("仓库中没有可用分支")
    if not default_branch:
        default_branch = "main" if "main" in branches else "master" if "master" in branches else branches[0]
    return GitRemoteInfo(_repository_name(url), branches, default_branch)


def list_remote_commits(
    *,
    repository_url: str,
    auth_type: str,
    credential: str | None,
    branch: str,
    start_at: datetime,
    end_at: datetime,
    limit: int,
) -> list[GitCommit]:
    host = _repository_host(repository_url)
    _validate_public_host(host)
    if not branch or branch.startswith("-") or any(token in branch for token in ("..", "~", "^", ":", "\\")):
        raise GitConnectionError("分支名称无效")

    commits: list[GitCommit] = []
    with tempfile.TemporaryDirectory(prefix="agent-platform-git-read-") as temp_dir:
        repository_path = Path(temp_dir) / "repository"
        with git_auth_environment(auth_type, credential) as env:
            _run_git(
                [
                    "clone",
                    "--quiet",
                    "--filter=blob:none",
                    "--no-checkout",
                    "--single-branch",
                    "--branch",
                    branch,
                    repository_url,
                    str(repository_path),
                ],
                env=env,
                timeout=60,
            )
            output = _run_git(
                [
                    "log",
                    "HEAD",
                    f"--since={start_at.isoformat()}",
                    f"--until={end_at.isoformat()}",
                    f"--max-count={limit}",
                    "--format=%H%x1f%an%x1f%ae%x1f%aI%x1f%s%x1e",
                ],
                cwd=repository_path,
                env=env,
                timeout=30,
            )
            remaining_patch_budget = MAX_PATCH_CHARS_TOTAL
            for record in output.strip("\n\x1e").split("\x1e"):
                if not record.strip():
                    continue
                fields = record.strip().split("\x1f", 4)
                if len(fields) != 5:
                    continue
                changed_files = _changed_files_for_commit(fields[0], repository_path=repository_path, env=env)
                patch = _patch_for_commit(
                    fields[0],
                    repository_path=repository_path,
                    env=env,
                    remaining_budget=remaining_patch_budget,
                )
                remaining_patch_budget = max(0, remaining_patch_budget - len(patch))
                commits.append(
                    GitCommit(
                        sha=fields[0],
                        author_name=fields[1],
                        author_email=fields[2],
                        authored_at=datetime.fromisoformat(fields[3]),
                        subject=fields[4],
                        changed_files=changed_files,
                        patch=patch,
                    )
                )
    return commits
