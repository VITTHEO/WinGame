"""
WinGame GitHub Releases Update Checker & Installer Downloader (BETA-0.16A).
Uses Python standard library urllib (zero external dependencies).
"""

import os
import re
import json
import tempfile
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, Tuple
from PyQt6.QtCore import QThread, pyqtSignal
from config import ConfigManager


APP_VERSION = "BETA-0.16A"
DEFAULT_GITHUB_REPO = "VITTHEO/Wingame"


def _parse_version_tuple(ver_str: str) -> Tuple[int, ...]:
    """Extracts numeric version parts (e.g. 'BETA-0.16A' -> (0, 16), 'v1.2.3' -> (1, 2, 3))."""
    nums = re.findall(r"\d+", ver_str or "")
    return tuple(int(n) for n in nums) if nums else (0,)


def is_newer_version(remote_tag: str, current_ver: str = APP_VERSION) -> bool:
    """Returns True if remote_tag is strictly newer than current_ver."""
    if not remote_tag:
        return False
    r_clean = remote_tag.strip().lstrip("vV")
    c_clean = current_ver.strip().lstrip("vV")
    if r_clean.lower() == c_clean.lower():
        return False
    r_nums = _parse_version_tuple(r_clean)
    c_nums = _parse_version_tuple(c_clean)
    if r_nums != c_nums:
        return r_nums > c_nums
    # Same numbers (e.g. BETA-0.16A vs BETA-0.16B) -> compare trailing letters
    return r_clean.lower() > c_clean.lower()


class UpdateEngine:
    @staticmethod
    def get_repo() -> str:
        repo = (ConfigManager().get("github_repo", DEFAULT_GITHUB_REPO) or "").strip()
        repo = repo.replace("https://github.com/", "").replace("http://github.com/", "").strip("/")
        return repo or DEFAULT_GITHUB_REPO

    @classmethod
    def check_latest_release(cls, repo_override: str = "") -> Dict[str, Any]:
        """Queries GitHub Releases API for the latest release of the configured repo."""
        repo = (repo_override or cls.get_repo()).strip().replace("https://github.com/", "").strip("/")
        if "/" not in repo:
            return {
                "status": "error",
                "message": "Invalid GitHub repo format. Expected 'username/repository'.",
                "current_version": APP_VERSION,
            }

        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": f"WinGame-Updater/{APP_VERSION}",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {
                    "status": "no_release",
                    "message": f"No GitHub release published yet for '{repo}'.",
                    "current_version": APP_VERSION,
                    "repo": repo,
                }
            return {
                "status": "error",
                "message": f"GitHub API error (HTTP {e.code}).",
                "current_version": APP_VERSION,
                "repo": repo,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Could not reach GitHub: {e}",
                "current_version": APP_VERSION,
                "repo": repo,
            }

        tag = data.get("tag_name") or data.get("name") or ""
        html_url = data.get("html_url") or f"https://github.com/{repo}/releases"
        notes = (data.get("body") or "").strip()

        # Look for WinGame_Installer.exe (or any .exe asset)
        installer_url = ""
        installer_name = ""
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            dl = asset.get("browser_download_url", "")
            if name.lower().endswith(".exe") and dl:
                installer_url = dl
                installer_name = name
                if "installer" in name.lower():
                    break

        update_avail = is_newer_version(tag, APP_VERSION)
        return {
            "status": "update_available" if update_avail else "up_to_date",
            "current_version": APP_VERSION,
            "latest_version": tag,
            "html_url": html_url,
            "installer_url": installer_url,
            "installer_name": installer_name,
            "notes": notes[:500],
            "repo": repo,
            "message": (
                f"New version {tag} is available! (Current: {APP_VERSION})"
                if update_avail
                else f"You are up to date ({APP_VERSION})."
            ),
        }

    @staticmethod
    def download_installer(download_url: str, filename: str = "WinGame_Installer.exe", progress_cb=None) -> Tuple[bool, str]:
        """Downloads the new WinGame_Installer.exe to %TEMP% and returns (ok, path_or_err)."""
        try:
            dst = os.path.join(tempfile.gettempdir(), filename or "WinGame_Installer.exe")
            req = urllib.request.Request(download_url, headers={"User-Agent": f"WinGame-Updater/{APP_VERSION}"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                downloaded = 0
                with open(dst, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_cb and total > 0:
                            progress_cb(int((downloaded / total) * 100))
            return True, dst
        except Exception as e:
            return False, str(e)


class UpdateCheckerThread(QThread):
    check_finished = pyqtSignal(dict)

    def __init__(self, repo_override: str = "", parent=None):
        super().__init__(parent)
        self.repo_override = repo_override

    def run(self):
        res = UpdateEngine.check_latest_release(repo_override=self.repo_override)
        self.check_finished.emit(res)


class UpdateDownloadThread(QThread):
    progress = pyqtSignal(int)
    download_finished = pyqtSignal(bool, str)

    def __init__(self, url: str, filename: str = "WinGame_Installer.exe", parent=None):
        super().__init__(parent)
        self.url = url
        self.filename = filename

    def run(self):
        ok, res = UpdateEngine.download_installer(self.url, self.filename, progress_cb=self.progress.emit)
        self.download_finished.emit(ok, res)
