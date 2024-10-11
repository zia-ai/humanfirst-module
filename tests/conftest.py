"""

Humanfirst tests conf

Solution to prevent clock skew issue when running aio container locally.

Clock skew issue explained in humanfirst_tests.py
"""
# ***************************************************************************80**************************************120
# conftest.py
import subprocess
import time
import pytest

def synchronize_time():
    """synchronize_time"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Use ntpdate command to synchronize time with an NTP server
            subprocess.run([
                "sudo", "ntpdate", "-u", "pool.ntp.org"
            ],
                check=True,
                stdout=subprocess.DEVNULL,  # Suppress standard output
                stderr=subprocess.PIPE  # Capture standard error for analysis
            )
            # If successful, break out of the retry loop
            return
        except subprocess.CalledProcessError as e:
            # Check if the error is related to rate limiting
            error_message = e.stderr.decode('utf-8').strip()
            if "no server suitable for synchronization found" in error_message:
                print(f"Rate limit hit, retrying... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s...
            else:
                # If it's another kind of error, print and exit loop
                print(f"Error occurred while synchronizing time: {error_message}")
                break
    else:
        # If all retries failed, print a final error message
        print("Failed to synchronize time after multiple attempts due to rate limiting or other errors.")

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_call(item):
    """pytest_runtest_call"""
    # Synchronize time before every test case
    synchronize_time()
    yield
