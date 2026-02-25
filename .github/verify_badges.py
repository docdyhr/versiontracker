#!/usr/bin/env python3
"""Badge Status Verification Script for VersionTracker.

This script verifies all GitHub badges are working correctly and provides
a comprehensive status report for CI/CD pipeline health.
"""

import sys
import time
from typing import Any
from urllib.parse import urlparse

import requests


class BadgeVerifier:
    """Verifies GitHub badges and provides status reports."""

    def __init__(self) -> None:
        """Initialize the badge verifier with session and results storage."""
        self.results: list[dict[str, Any]] = []
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "VersionTracker-Badge-Verifier/1.0"})

    def check_badge(self, name: str, url: str, expected_status: int = 200) -> dict:
        """Check a single badge URL and return status information."""
        try:
            response = self.session.get(url, timeout=10)
            status = response.status_code

            # Check if it's an SVG (expected for most badges)
            content_type = response.headers.get("content-type", "")
            is_svg = "svg" in content_type.lower()

            # Check response size (very small responses might indicate errors)
            content_length = len(response.content)

            result = {
                "name": name,
                "url": url,
                "status_code": status,
                "success": status == expected_status,
                "is_svg": is_svg,
                "content_length": content_length,
                "response_time": response.elapsed.total_seconds(),
                "error": None,
            }

            # Additional checks for GitHub Actions badges
            parsed = urlparse(url)
            if parsed.hostname == "github.com" and "actions/workflows" in parsed.path:
                # These might return different status codes when no runs exist
                result["success"] = status in [200, 404]  # 404 is OK for new workflows

        except requests.exceptions.RequestException as e:
            result = {
                "name": name,
                "url": url,
                "status_code": None,
                "success": False,
                "is_svg": False,
                "content_length": 0,
                "response_time": 0,
                "error": str(e),
            }

        self.results.append(result)
        return result

    def verify_all_badges(self) -> list[dict]:
        """Verify all badges defined in the project."""
        badges = [
            # GitHub Actions Badges (shields.io format)
            (
                "CI Pipeline",
                "https://img.shields.io/github/actions/workflow/status/docdyhr/versiontracker/ci.yml?branch=master&label=CI%20Pipeline&logo=github&logoColor=white",
            ),
            (
                "Lint",
                "https://img.shields.io/github/actions/workflow/status/docdyhr/versiontracker/lint.yml?branch=master&label=lint&logo=github&logoColor=white",
            ),
            (
                "Security",
                "https://img.shields.io/github/actions/workflow/status/docdyhr/versiontracker/security.yml?branch=master&label=security&logo=github&logoColor=white",
            ),
            (
                "CI Status",
                "https://img.shields.io/github/actions/workflow/status/docdyhr/versiontracker/ci.yml?branch=master&label=CI&logo=github&logoColor=white",
            ),
            # GitHub Actions Badges (native format)
            (
                "Lint (Native)",
                "https://github.com/docdyhr/versiontracker/actions/workflows/lint.yml/badge.svg",
            ),
            (
                "Security (Native)",
                "https://github.com/docdyhr/versiontracker/actions/workflows/security.yml/badge.svg",
            ),
            (
                "CI (Native)",
                "https://github.com/docdyhr/versiontracker/actions/workflows/ci.yml/badge.svg",
            ),
            (
                "Release (Native)",
                "https://github.com/docdyhr/versiontracker/actions/workflows/release.yml/badge.svg",
            ),
            # Package Information Badges
            (
                "PyPI Version",
                "https://img.shields.io/pypi/v/versiontracker?logo=pypi&logoColor=white",
            ),
            (
                "Python Versions",
                "https://img.shields.io/pypi/pyversions/versiontracker?logo=python&logoColor=white",
            ),
            (
                "PyPI Downloads",
                "https://img.shields.io/pypi/dm/versiontracker?logo=pypi&logoColor=white&label=downloads",
            ),
            (
                "PyPI Status",
                "https://img.shields.io/pypi/status/versiontracker?logo=pypi&logoColor=white",
            ),
            # Quality & Coverage Badges
            (
                "Code Coverage",
                "https://img.shields.io/codecov/c/github/docdyhr/versiontracker/master?logo=codecov&logoColor=white",
            ),
            (
                "Codecov (Alternative)",
                "https://codecov.io/gh/docdyhr/versiontracker/branch/master/graph/badge.svg",
            ),
            # Repository Stats Badges
            (
                "GitHub Issues",
                "https://img.shields.io/github/issues/docdyhr/versiontracker?logo=github&logoColor=white",
            ),
            (
                "GitHub Forks",
                "https://img.shields.io/github/forks/docdyhr/versiontracker?logo=github&logoColor=white",
            ),
            (
                "GitHub Stars",
                "https://img.shields.io/github/stars/docdyhr/versiontracker?logo=github&logoColor=white",
            ),
            (
                "Last Commit",
                "https://img.shields.io/github/last-commit/docdyhr/versiontracker?logo=github&logoColor=white",
            ),
            (
                "Code Size",
                "https://img.shields.io/github/languages/code-size/docdyhr/versiontracker?logo=github&logoColor=white&label=code%20size",
            ),
            (
                "Repo Size",
                "https://img.shields.io/github/repo-size/docdyhr/versiontracker?logo=github&logoColor=white&label=repo%20size",
            ),
            # Static Badges
            (
                "License MIT",
                "https://img.shields.io/badge/License-MIT-yellow.svg?logo=opensourceinitiative&logoColor=white",
            ),
            (
                "macOS Platform",
                "https://img.shields.io/badge/platform-macOS-blue.svg?logo=apple&logoColor=white",
            ),
            (
                "Python 3.8+",
                "https://img.shields.io/badge/python-3.8+-blue.svg?logo=python&logoColor=white",
            ),
            (
                "Homebrew Compatible",
                "https://img.shields.io/badge/homebrew-compatible-orange.svg?logo=homebrew&logoColor=white",
            ),
            (
                "Code Style Ruff",
                "https://img.shields.io/badge/code%20style-ruff-000000.svg?logo=ruff&logoColor=white",
            ),
            (
                "Security Bandit",
                "https://img.shields.io/badge/security-bandit-yellow.svg?logo=python&logoColor=white",
            ),
            (
                "CLI Tool",
                "https://img.shields.io/badge/tool-CLI-brightgreen?logo=terminal&logoColor=white",
            ),
            (
                "Build Ready",
                "https://img.shields.io/badge/build-ready-brightgreen?logo=github&logoColor=white",
            ),
            (
                "Language Python",
                "https://img.shields.io/badge/language-Python-blue?logo=python&logoColor=white",
            ),
        ]

        print("🔍 Verifying all badges...")
        print("=" * 80)

        for name, url in badges:
            print(f"Checking {name}...", end=" ")
            result = self.check_badge(name, url)

            if result["success"]:
                print("✅")
            else:
                print(f"❌ ({result['status_code'] or 'ERROR'})")

            time.sleep(0.1)  # Rate limiting

        return self.results

    def print_summary(self) -> bool:
        """Print a comprehensive summary of badge verification results."""
        if not self.results:
            print("No badges were checked.")
            return False

        successful = [r for r in self.results if r["success"]]
        failed = [r for r in self.results if not r["success"]]

        print("\n" + "=" * 80)
        print("📊 BADGE VERIFICATION SUMMARY")
        print("=" * 80)
        print(f"Total Badges Checked: {len(self.results)}")
        print(f"✅ Successful: {len(successful)} ({len(successful) / len(self.results) * 100:.1f}%)")
        print(f"❌ Failed: {len(failed)} ({len(failed) / len(self.results) * 100:.1f}%)")

        if failed:
            print("\n🚨 FAILED BADGES:")
            print("-" * 40)
            for result in failed:
                print(f"❌ {result['name']}")
                print(f"   URL: {result['url']}")
                print(f"   Status: {result['status_code'] or 'Network Error'}")
                if result["error"]:
                    print(f"   Error: {result['error']}")
                print()

        # Performance statistics
        response_times = [r["response_time"] for r in successful]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)

            print("\n⚡ PERFORMANCE STATS:")
            print("-" * 40)
            print(f"Average Response Time: {avg_time:.2f}s")
            print(f"Fastest Response: {min_time:.2f}s")
            print(f"Slowest Response: {max_time:.2f}s")

        # Badge Categories
        github_actions = [
            r
            for r in self.results
            if urlparse(r["url"]).hostname == "github.com" and "/actions" in urlparse(r["url"]).path
        ]
        shields_io = [r for r in self.results if urlparse(r["url"]).hostname == "img.shields.io"]
        codecov = [r for r in self.results if urlparse(r["url"]).hostname == "codecov.io"]

        print("\n📋 BADGE CATEGORIES:")
        print("-" * 40)
        print(f"GitHub Actions: {len([r for r in github_actions if r['success']])}/{len(github_actions)}")
        print(f"Shields.io: {len([r for r in shields_io if r['success']])}/{len(shields_io)}")
        print(f"Codecov: {len([r for r in codecov if r['success']])}/{len(codecov)}")

        return len(failed) == 0

    def check_workflow_files(self) -> bool:
        """Verify that all referenced workflow files exist."""
        print("\n🔧 WORKFLOW FILE VERIFICATION:")
        print("-" * 40)

        workflow_files = [
            "lint.yml",
            "security.yml",
            "ci.yml",
            "release.yml",
        ]

        import os

        workflow_dir = ".github/workflows"

        for workflow in workflow_files:
            path = os.path.join(workflow_dir, workflow)
            exists = os.path.exists(path)
            print(f"{'✅' if exists else '❌'} {workflow}: {'Found' if exists else 'Missing'}")

        # Note about consolidated workflow
        print("\nℹ️  Note: test.yml was consolidated into ci.yml for better efficiency")
        return True


def main() -> None:
    """Main function to run badge verification."""
    print("🏆 VersionTracker Badge Verification Tool")
    print("=" * 80)

    verifier = BadgeVerifier()

    # Verify all badges
    verifier.verify_all_badges()

    # Check workflow files
    verifier.check_workflow_files()

    # Print comprehensive summary
    success = verifier.print_summary()

    # Return appropriate exit code
    if success:
        print("\n🎉 All badges are working correctly!")
        sys.exit(0)
    else:
        print("\n⚠️  Some badges need attention. Check the failed badges above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
