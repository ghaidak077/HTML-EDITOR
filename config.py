"""
Central config for values likely to change across phases.
Keep this the single source of truth — don't hardcode these elsewhere.
"""

APP_TITLE = "Visual HTML Editor"
WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 900
WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 640

# Phase 7 will use this (autosave interval, in seconds)
AUTOSAVE_INTERVAL_SECONDS = 30

# Phase 4 will use this (undo/redo history depth)
UNDO_STACK_SIZE = 50

# Phase 4 (responsive preview breakpoints, in px)
BREAKPOINT_TABLET = 768
BREAKPOINT_MOBILE = 375

# Storage paths, relative to the app's working directory
DRAFTS_DIR = "drafts"
COMPONENTS_DIR = "components"
CURRENT_DRAFT_FILE = "current.json"
