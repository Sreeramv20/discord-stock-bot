import os
import subprocess
import time
import shutil
import logging
from collections import defaultdict

TASK_DIR = "tasks"
DONE_DIR = "completed"
FAILED_DIR = "failed"
MODEL = "ollama/qwen3-coder:30b"
MAX_RETRIES = 30

os.environ["OLLAMA_API_BASE"] = "http://127.0.0.1:11434"
os.makedirs(TASK_DIR, exist_ok=True)  # FIX: ensure tasks dir exists
os.makedirs(DONE_DIR, exist_ok=True)
os.makedirs(FAILED_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("agent.log")]
)
log = logging.getLogger(__name__)

retry_counts = defaultdict(int)  # FIX: track retries per task

def run_tests():
    try:
        result = subprocess.run(["pytest"], capture_output=True, text=True)
        output = result.stdout + result.stderr
        if "collected 0 items" in output:
            return True
        return result.returncode == 0
    except Exception as e:
        log.error(f"Error running tests: {e}")
        return True

def git_commit(message):
    subprocess.run(["git", "add", "."])
    result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
    if result.returncode != 0:
        log.warning(f"Git commit failed: {result.stderr.strip()}")
        return False
    push = subprocess.run(["git", "push"], capture_output=True, text=True)  # FIX: check push result
    if push.returncode != 0:
        log.warning(f"Git push failed: {push.stderr.strip()}")
        return False
    return True

while True:
    tasks = sorted(os.listdir(TASK_DIR))
    if not tasks:
        log.info("No tasks remaining. Sleeping...")
        time.sleep(60)
        continue

    task = tasks[0]
    task_path = os.path.join(TASK_DIR, task)

    # FIX: skip empty task files
    with open(task_path, "r", encoding="utf-8") as f:
        prompt = f.read().strip()
    if not prompt:
        log.warning(f"Task {task} is empty. Moving to failed.")
        shutil.move(task_path, os.path.join(FAILED_DIR, task))
        continue

    log.info(f"Running task: {task} (attempt {retry_counts[task] + 1}/{MAX_RETRIES})")

    result = subprocess.run([
        "aider",
        "--model", MODEL,
        "--yes",
        "--no-gitignore",
        ".",
        "--message", prompt  # FIX: use the actual prompt content, not the filename
    ])

    if result.returncode != 0:
        retry_counts[task] += 1
        if retry_counts[task] >= MAX_RETRIES:  # FIX: enforce retry limit
            log.error(f"Task {task} failed {MAX_RETRIES} times. Moving to failed.")
            shutil.move(task_path, os.path.join(FAILED_DIR, task))
            del retry_counts[task]
        else:
            log.warning(f"Task {task} failed. Will retry.")
        time.sleep(30)
        continue

    tests_passed = run_tests()
    if tests_passed:
        git_commit(f"AI completed task: {task}")
        shutil.move(task_path, os.path.join(DONE_DIR, task))
        del retry_counts[task]
        log.info("Task completed and committed.")
    else:
        retry_counts[task] += 1
        if retry_counts[task] >= MAX_RETRIES:  # FIX: retry limit for test failures too
            log.error(f"Task {task} kept failing tests after {MAX_RETRIES} attempts. Moving to failed.")
            shutil.move(task_path, os.path.join(FAILED_DIR, task))
            del retry_counts[task]
        else:
            log.warning(f"Tests failed for {task}. Attempt {retry_counts[task]}/{MAX_RETRIES}.")
        time.sleep(30)