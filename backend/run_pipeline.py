import subprocess
import sys
import os


def run_step(command: list[str], step_name: str) -> bool:
    """Runs a subprocess shell command, printing output and return status."""
    print("==================================================================")
    print(f" Running Quality Step: {step_name}")
    print(f" Command: {' '.join(command)}")
    print("------------------------------------------------------------------")

    try:
        # Run process, pipe output directly to stdout/stderr
        result = subprocess.run(
            command,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=False,
            text=True,
        )

        if result.returncode == 0:
            print("------------------------------------------------------------------")
            print(f" STATUS: SUCCESS")
            print(
                "==================================================================\n"
            )
            return True
        else:
            print("------------------------------------------------------------------")
            print(f" STATUS: FAILED (Exit Code {result.returncode})")
            print(
                "==================================================================\n"
            )
            return False

    except FileNotFoundError:
        print("------------------------------------------------------------------")
        print(
            f" STATUS: FAILED (Executable not found. Make sure dependencies are installed.)"
        )
        print("==================================================================\n")
        return False


def main():
    print("==================================================================")
    print("        Project Nexus26 Automated Quality Pipeline Gateway        ")
    print("==================================================================\n")

    # Step 1: Code Formatting Check (Black)
    # We verify that files conform to Black standard style guidelines
    format_cmd = [
        sys.executable,
        "-m",
        "black",
        "--check",
        "app",
        "tests",
        "load_generator.py",
    ]
    format_ok = run_step(format_cmd, "Code Formatting Check (Black)")

    # Step 2: Code Linting (Flake8)
    # Checks for pep8 syntax guidelines, unused imports, and syntax warnings
    lint_cmd = [sys.executable, "-m", "flake8", "app", "tests", "--max-line-length=120"]
    lint_ok = run_step(lint_cmd, "Code Linting Check (Flake8)")

    # Step 3: Run Pytest Suites
    # Executes all unit and integration test modules
    test_cmd = [sys.executable, "-m", "pytest", "tests"]
    tests_ok = run_step(test_cmd, "Automated Test Suites Execution (PyTest)")

    # Consolidate results
    print("==================================================================")
    print("                  QUALITY PIPELINE EXECUTION SUMMARY              ")
    print("==================================================================")
    print(f" 1. Code Formatting (Black): {'PASSED' if format_ok else 'FAILED'}")
    print(f" 2. Code Linting (Flake8):    {'PASSED' if lint_ok else 'FAILED'}")
    print(f" 3. Unit & Integration Tests: {'PASSED' if tests_ok else 'FAILED'}")
    print("------------------------------------------------------------------")

    if format_ok and lint_ok and tests_ok:
        print(" PIPELINE RESULT: ALL STEPS PASSED SUCCESSFULLY. CODE READY FOR DEPLOY.")
        print("==================================================================")
        sys.exit(0)
    else:
        print(" PIPELINE RESULT: FAILURE DETECTED. PLEASE CORRECT LINTS/TESTS.")
        print("==================================================================")
        sys.exit(1)


if __name__ == "__main__":
    main()
