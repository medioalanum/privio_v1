"""Cross-platform script runner for linting, formatting, and type checks."""

import subprocess
import sys


def run_command(cmd: list[str], description: str) -> None:
    """Execute a command and exit with error code if failed."""
    print(f"\n==> {description} ({' '.join(cmd)})")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(
            f"Error: {description} failed with return code {result.returncode}",
            file=sys.stderr,
        )
        sys.exit(result.returncode)


def main() -> None:
    """Run all quality checks."""
    print("======================================")
    print(" Running Quality & Type Checks")
    print("======================================")

    run_command(["ruff", "check", "."], "Ruff Linter Check")
    run_command(["ruff", "format", "--check", "."], "Ruff Format Check")
    run_command(["ty", "check", "."], "Astral ty Type Checker")

    print("\n All checks passed successfully!")


if __name__ == "__main__":
    main()
