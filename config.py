# Timing
CAPTURE_INTERVAL_MS      = 8_000   # ms between AI analysis calls
CAPTURE_MAX_DIMENSION    = 768     # px; capture is downscaled so longest side fits this before sending to LLM
ANIMATION_TICK_MS        = 16      # ~60 fps
WINDOW_TRACK_INTERVAL_MS = 500     # how often overlay re-syncs to target window rect
COMMENT_SPAWN_DELAY      = 300     # ms stagger between comments in the same batch

# Comment physics (pixels per animation tick)
COMMENT_SPEED_MIN = 4
COMMENT_SPEED_MAX = 8

# Lanes
LANE_COUNT   = 10
LANE_PADDING = 4  # vertical px padding from top/bottom

# Font
FONT_FAMILY = "Yu Gothic UI"  # ships with Win10/11, handles Japanese
FONT_SIZE_MIN = 22
FONT_SIZE_MAX = 36
FONT_BOLD = True

# Colors: RGBA tuples
COMMENT_COLORS = [
    (255, 255, 255, 255),  # white (most common)
    (255, 255, 100, 255),  # yellow
    (100, 220, 255, 255),  # cyan
    (255, 130, 130, 255),  # pink/red
    (150, 255, 150, 255),  # green
]
OUTLINE_COLOR = (0, 0, 0, 200)  # semi-transparent black
OUTLINE_WIDTH = 3

# Performance logging — writes CSV rows to PERF_LOG_PATH (relative to project dir)
PERF_LOG_ENABLED = True
PERF_LOG_PATH    = "perf.csv"

# Ollama (local LLM — no API key required)
OLLAMA_MODEL = "gemma4"         # change to "gemma4:12b" for higher quality, "moondream" for lighter
OLLAMA_HOST  = "http://localhost:11434"  # default Ollama server
OLLAMA_PROMPT = (
    "You are generating NicoNico-style viewer comments for what is happening on screen. "
    "Look at this screenshot and generate 5 short, punchy, Japanese-style comments "
    "(each under 20 characters) that viewers might type while watching this content. "
    "Mix reaction comments (wwww, すごい, etc.) with content-specific observations. "
    "Return ONLY the 5 comments, one per line, no numbering, no explanation."
)
