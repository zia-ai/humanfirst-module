"""

Humanfirst tests conf

Solution to prevent clock skew issue when running aio container locally.

Clock skew issue explained in humanfirst_tests.py
"""
# ***************************************************************************80**************************************120
# conftest.py
import pytest
import subprocess

def synchronize_time():
    try:
        # Use ntpdate command to synchronize time with an NTP server
        subprocess.run(["sudo", "ntpdate", "-u", "pool.ntp.org"],
                       check=True,
                       stdout=subprocess.DEVNULL,  # Suppress standard output
                    #    stderr=subprocess.DEVNULL   # Suppress standard error
        )
        # print("Time synchronized with NTP server")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while synchronizing time: {e}")

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_call(item):
    # Synchronize time before every test case
    synchronize_time()
    yield