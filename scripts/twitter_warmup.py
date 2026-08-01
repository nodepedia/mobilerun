#!/usr/bin/env python3
"""Twitter/X Warm-Up Scheduler

Runs a daily loop of 4 warm-up tasks from 6:00 to 21:00.
Each cycle: Task1 -> cooldown -> Task2 -> cooldown -> Task3 -> cooldown -> Task4 -> cooldown -> repeat.
Tweet is only posted during the first cycle of the day.

Usage:
    python scripts/twitter_warmup.py

Schedule via cron (run every day at 6:00 AM):
    0 6 * * * cd /path/to/mobilerun && python scripts/twitter_warmup.py >> logs/twitter_warmup.log 2>&1
"""

import random
import subprocess
import sys
import time
from datetime import datetime, timedelta

# ============================================================
# Configuration
# ============================================================

CONFIG_PATH = "config/twitter_warmup.yaml"
MAX_STEPS = 200

START_HOUR = 6
END_HOUR = 21

COOLDOWN_MIN_MINUTES = 20
COOLDOWN_MAX_MINUTES = 50

# Keyword pools
GENERAL_KEYWORDS = [
    "viral hari ini",
    "fakta unik",
    "quotes inspiratif",
    "motivasi hidup",
    "kata kata bijak",
    "thread menarik",
    "rekomendasi film",
    "rekomendasi buku",
    "tips produktivitas",
    "teknologi terbaru",
    "startup indonesia",
    "kisah sukses",
    "belajar coding",
    "pengembangan diri",
    "mental health",
]

FOLLOW_KEYWORDS = [
    "cenblu",
    "jb jb",
    "mari follow",
    "follow dulu",
    "mutualan",
    "follback",
    "auto follback",
    "saling follow",
    "need mutuals",
    "let's be mutuals",
]


# ============================================================
# Task Prompt Builders
# ============================================================

def build_task1_prompt():
    """Task 1: Morning browse - trending + following feed."""
    return (
        "Open Twitter/X app. Go to the Search tab and read the trending topics for "
        "about 1-2 minutes (scroll through the trends list). "
        "Then go to the Home tab, switch to the 'Following' feed, and scroll through "
        "tweets from people you follow for 2-3 minutes. "
        "Like 2-3 tweets that seem interesting. "
        "Use the wait tool between scrolls to simulate reading. "
        "When done, press the home button to close the app. "
        "Call complete with success=true."
    )


def build_task2_prompt():
    """Task 2: Search keyword + read + like + reply."""
    keyword = random.choice(GENERAL_KEYWORDS)
    return (
        f"Open Twitter/X app. Go to the Search tab and search for '{keyword}'. "
        f"Select the 'Top' tab to see the most relevant results. "
        f"Scroll through 5-7 tweets from the search results, reading them naturally "
        f"(use wait tool between scrolls, 3-8 seconds each). "
        f"Like 1-2 tweets that are interesting. "
        f"Open one tweet by tapping on it, read the replies. "
        f"Reply to the tweet with a short, casual comment (5-15 words) relevant to its content. "
        f"After replying, press the back button to return to search results. "
        f"When done, press the home button to close the app. "
        f"Call complete with success=true."
    )


def build_task3_prompt():
    """Task 3: Follow accounts via mutualan keywords."""
    keyword = random.choice(FOLLOW_KEYWORDS)
    follow_count = random.randint(2, 5)
    return (
        f"Open Twitter/X app. Go to the Search tab and search for '{keyword}'. "
        f"Select the 'Latest' tab to see the most recent tweets. "
        f"Tap on the first tweet to open its detail page. "
        f"Follow the tweet creator by tapping the 'Follow' button next to their name. "
        f"Then scroll down to the replies section and follow users who replied "
        f"(tap 'Follow' next to each replier's name). "
        f"Follow about {follow_count} accounts total in this session. "
        f"Do not follow more than {follow_count + 2} accounts. "
        f"Skip accounts that are already followed. "
        f"Do not follow accounts that look like bots or spam. "
        f"When done or when you've followed enough, press back to return to search results, "
        f"then press the home button to close the app. "
        f"Call complete with success=true."
    )


def build_task4_prompt(is_first_cycle):
    """Task 4: Evening trending check + optional tweet."""
    if is_first_cycle:
        return (
            "Open Twitter/X app. Go to the Search tab and check what's trending today. "
            "Read the top 5-7 trending topics and pick one that interests you. "
            "Go back to the Home tab. Tap the compose button (the '+' floating button "
            "at bottom-right). "
            "Write a tweet about the trending topic you picked. The tweet should be "
            "10-15 sentences long, written in a casual personal style with your own opinion. "
            "Do NOT use any hashtags at all. "
            "Do NOT copy text from anywhere - write original content. "
            "After typing, tap the 'Post' button to publish the tweet. "
            "When done, press the home button to close the app. "
            "Call complete with success=true."
        )
    else:
        return (
            "Open Twitter/X app. Go to the Search tab and check the trending topics "
            "for 1-2 minutes. Read what's being discussed. "
            "Then go to the Home tab and scroll the 'For You' feed for 1-2 minutes. "
            "Like 1 tweet if you see something interesting. "
            "Do NOT post any tweet in this session. "
            "When done, press the home button to close the app. "
            "Call complete with success=true."
        )


# ============================================================
# Runner
# ============================================================

TASK_TIMEOUT_SECONDS = 900  # 15 minutes per task max

def run_task(prompt, task_name):
    """Execute a single warm-up task via mobilerun CLI."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n{'='*60}")
    print(f"[{timestamp}] START: {task_name}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            [
                "mobilerun", "run",
                "-c", CONFIG_PATH,
                "--steps", str(MAX_STEPS),
                prompt,
            ],
            capture_output=False,
            text=True,
            timeout=TASK_TIMEOUT_SECONDS,
        )
        success = result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] Task exceeded {TASK_TIMEOUT_SECONDS}s limit — killed.")
        return False
    except FileNotFoundError:
        print(f"[ERROR] mobilerun command not found. Make sure it's installed.")
        return False
    except Exception as e:
        print(f"[ERROR] Task failed with exception: {e}")
        return False

    timestamp = datetime.now().strftime("%H:%M:%S")
    status = "SUCCESS" if success else "FAILED"
    print(f"\n[{timestamp}] END: {task_name} -> {status}")
    return success


def cooldown():
    """Random cooldown between 30-90 minutes."""
    wait_seconds = random.randint(
        COOLDOWN_MIN_MINUTES * 60,
        COOLDOWN_MAX_MINUTES * 60,
    )
    wait_minutes = wait_seconds // 60
    end_time = datetime.now() + timedelta(seconds=wait_seconds)
    end_time_str = end_time.strftime("%H:%M:%S")
    print(f"\n[COOLDOWN] Waiting {wait_minutes} minutes (until ~{end_time_str})...")

    time.sleep(wait_seconds)


def is_within_time_window():
    """Check if current time is within the active window (6:00 - 21:00)."""
    now = datetime.now()
    return START_HOUR <= now.hour < END_HOUR


# ============================================================
# Main Loop
# ============================================================

def run_daily_warmup():
    """Run the full daily warm-up loop from 6:00 to 21:00."""
    cycle_number = 0

    print(f"\n{'#'*60}")
    print(f"# Twitter Warm-Up Scheduler Started")
    print(f"# Time window: {START_HOUR:02d}:00 - {END_HOUR:02d}:00")
    print(f"# Config: {CONFIG_PATH}")
    print(f"# Cooldown: {COOLDOWN_MIN_MINUTES}-{COOLDOWN_MAX_MINUTES} min")
    print(f"{'#'*60}")

    while is_within_time_window():
        cycle_number += 1
        now_str = datetime.now().strftime("%H:%M:%S")
        print(f"\n{'*'*60}")
        print(f"* CYCLE {cycle_number} started at {now_str}")
        print(f"{'*'*60}")

        is_first = cycle_number == 1

        # Task 1: Trending + Following feed
        if is_within_time_window():
            if not run_task(build_task1_prompt(), "Task 1: Trending + Following Feed"):
                print("[WARN] Task 1 failed — continuing to next task.")
        if is_within_time_window():
            cooldown()

        # Task 2: Search keyword + like + reply
        if is_within_time_window():
            if not run_task(build_task2_prompt(), "Task 2: Search Keyword + Like + Reply"):
                print("[WARN] Task 2 failed — continuing to next task.")
        if is_within_time_window():
            cooldown()

        # Task 3: Follow accounts
        if is_within_time_window():
            if not run_task(build_task3_prompt(), "Task 3: Follow Accounts (2-5)"):
                print("[WARN] Task 3 failed — continuing to next task.")
        if is_within_time_window():
            cooldown()

        # Task 4: Tweet (first cycle) or Browse trending (subsequent)
        if is_within_time_window():
            task4_name = "Task 4: Post Tweet" if is_first else "Task 4: Browse Trending (no tweet)"
            if not run_task(build_task4_prompt(is_first), task4_name):
                print("[WARN] Task 4 failed — continuing to next task.")
        if is_within_time_window():
            cooldown()

    end_str = datetime.now().strftime("%H:%M:%S")
    print(f"\n{'#'*60}")
    print(f"# Daily warm-up completed at {end_str}")
    print(f"# Total cycles: {cycle_number}")
    print(f"# Next run: tomorrow at {START_HOUR:02d}:00")
    print(f"{'#'*60}")


if __name__ == "__main__":
    run_daily_warmup()
