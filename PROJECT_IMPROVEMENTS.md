# Code Quality & Readability Improvements

A pragmatic review focused on reducing cognitive load through better naming, smaller functions, clearer module boundaries, and less duplication.

---

## Top 10 Improvements

### 1. Duplicate CSS Files in Static Directory

**Files:**
- `whisper_video_to_text/web/static/style.css`
- `whisper_video_to_text/web/static/styles.css`

**Why:** Two stylesheets with nearly identical purposes cause confusion. Only `style.css` is actually used in `index.html`. `styles.css` appears to be dead code.

**How:** Delete `styles.css` or merge useful utilities into `style.css`.

```bash
rm whisper_video_to_text/web/static/styles.css
```

---

### 2. Hardcoded `~/research` Directory in CLI

**File:** `cli.py` (lines 108-112)

**Why:** The default output goes to a hardcoded `~/research` directory. This is unexpected behavior and may confuse users—they'll wonder where their files went.

**How:** Default to the current working directory or the same directory as the input file:

```python
# Before
research_dir = Path.home() / "research"
research_dir.mkdir(exist_ok=True)
timestamp = int(time.time())
base = research_dir / f"transcript-{timestamp}"

# After
output_dir = video_path.parent
timestamp = int(time.time())
base = output_dir / f"{video_path.stem}-transcript-{timestamp}"
```

---

### 3. Misleading Function Name: `background_stub`

**File:** `web/views.py` (line 40)

**Why:** The name `background_stub` suggests it's a placeholder/mock, but it's the real implementation. This confuses readers.

**How:** Rename to `process_transcription_job` or `run_transcription_task`:

```python
def run_transcription_task(
    job_id,
    file=None,
    url=None,
    model="base",
    language=None,
    formats=None,
    timestamps=False,
):
```

---

### 4. `asyncio.run()` Inside a Thread Called from Async Context

**File:** `web/views.py` (line 85)

**Why:** `background_stub` uses `asyncio.run(run())` inside what FastAPI's `BackgroundTasks` runs in a thread pool. This is fragile and can cause issues with event loops. The function mixes sync/async paradigms unnecessarily.

**How:** Make the function fully synchronous—use direct function calls instead of `async/await`:

```python
def run_transcription_task(job_id, ...):
    tempdir = tempfile.mkdtemp(prefix="wvttmp_")
    try:
        # Use synchronous helper or run_in_executor for progress updates
        ...
```

Or convert to a proper async task runner.

---

### 5. Time Formatting Logic is Duplicated

**File:** `transcribe.py` (lines 122-135)

**Why:** `_format_srt_time` and `_format_vtt_time` are nearly identical (only difference: `,` vs `.` for milliseconds). This duplicates ~12 lines.

**How:** Extract a shared helper:

```python
def _format_time(seconds: float, ms_sep: str = ",") -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02}{ms_sep}{ms:03}"

def _format_srt_time(seconds: float) -> str:
    return _format_time(seconds, ",")

def _format_vtt_time(seconds: float) -> str:
    return _format_time(seconds, ".")
```

---

### 6. In-Memory Global State for Jobs

**File:** `web/progress.py` (line 5)

**Why:** `jobs = {}` is a global mutable dict. This works for single-process deployments but will silently fail with multiple workers. A comment warning about this would help future maintainers.

**How:** Add a docstring/comment clarifying the limitation:

```python
# In-memory job state. NOTE: Only works with single-worker deployment.
# For multi-worker, migrate to Redis or database-backed storage.
jobs: dict[str, JobState] = {}
```

---

### 7. Broad `except Exception` in CLI and Web

**Files:**
- `cli.py` (lines 135-137)
- `web/views.py` (line 80)

**Why:** Catching bare `Exception` hides specific errors and makes debugging harder. The logging message is also vague.

**How:** At minimum, log the full traceback:

```python
except Exception as e:
    logging.exception(f"✗ Error during transcription: {e}")
    sys.exit(1)
```

Or catch specific exceptions (`FileNotFoundError`, `subprocess.CalledProcessError`, etc.) with targeted messages.

---

### 8. `--format` Default Behavior is Confusing

**File:** `cli.py` (lines 67-72)

**Why:** The argument has `default=["txt"]` but also `action="append"`. When a user specifies `--format srt`, they get `["txt", "srt"]` instead of just `["srt"]`. This is a bug masked by `set()` on line 115.

**How:** Change to a proper list-based approach:

```python
parser.add_argument(
    "--format",
    action="append",
    choices=["txt", "srt", "vtt"],
    default=None,  # NOT ["txt"]
    help="Output format(s). Can be specified multiple times. (default: txt)",
)
# ...
formats = args.format if args.format else ["txt"]
for fmt in set(formats):
```

---

### 9. Unused Parameters in `background_stub`

**File:** `web/views.py` (lines 46-47)

**Why:** `formats` and `timestamps` parameters are passed but never used inside the function. This is misleading—the web API suggests it supports these options but doesn't.

**How:** Either implement the functionality or remove the parameters (and update the API):

```python
# Either implement:
if "srt" in formats:
    save_srt(result, ...)
    
# Or remove unused params and update form handling
```

---

### 10. Inconsistent Import of `ffmpeg` (Inside Function)

**File:** `convert.py` (lines 32-37)

**Why:** `import ffmpeg` is done inside the function, then wrapped in `try/except`. If the import fails silently, users won't know `ffmpeg-python` is missing. This hides a dependency issue.

**How:** Add a clear warning or make it a proper optional dependency check:

```python
try:
    import ffmpeg
    HAS_FFMPEG_PYTHON = True
except ImportError:
    HAS_FFMPEG_PYTHON = False
    logging.debug("ffmpeg-python not installed; progress bar disabled")
```

Then use `HAS_FFMPEG_PYTHON` flag instead of repeated try/except.

---

## Quick Wins (≤1 hour)

- [x] Delete `styles.css` (dead code)
- [x] Rename `background_stub` → `run_transcription_task`
- [x] Add comment to `jobs = {}` about single-worker limitation
- [x] Fix `--format` default to `None` instead of `["txt"]`
- [x] Use `logging.exception()` instead of `logging.error()` in exception handlers
- [x] Extract shared `_format_time()` helper for SRT/VTT

---

## Deeper Refactors (half-day+)

- [x] Refactor `background_stub` to be fully synchronous or properly async (threading/asyncio cleanup)
- [x] Remove or implement `formats`/`timestamps` params in web API
- [x] Change default output directory from `~/research` to current directory (requires updating tests/docs)
- [x] Add proper optional dependency handling for `ffmpeg-python` with user-facing warning
- [x] Add type hints to web module functions (currently missing)

