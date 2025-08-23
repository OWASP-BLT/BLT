from website.models import InstallationState, RepoState

# Extensions for files that should generally be processed as text.
# This includes source code, web files, config files, and documentation.
EXTENSIONS_TO_PROCESS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".c",
    ".cpp",
    ".h",
    ".cs",
    ".swift",
    ".php",
    ".rb",
    ".sh",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".less",
    ".yml",
    ".yaml",
    ".json",
    ".ini",
    ".env",
    ".csv",
    ".xml",
    ".md",
    ".txt",
    ".gitignore",
    ".gitattributes",
    ".dockerfile",
}

# Explicit files to skip, regardless of extension.
# Includes lock files, build artifacts, and other non-source files.
SKIP_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "Cargo.lock",
    "composer.lock",
    "Gemfile.lock",
    "go.sum",
    "go.mod",
    "environment.yml",
    "setup.cfg",
    "Makefile",
    "CMakeLists.txt",
    "build.gradle",
    "pom.xml",
    ".coverage",
    "coverage.xml",
    ".yarn.lock",
}

# Directories to skip entirely to avoid large, irrelevant content.
# Includes dependency folders, build artifacts, caches, and static assets.
SKIP_DIRS = {
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "vendor",
    "dist",
    "build",
    "target",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "coverage",
    "static",
    "staticfiles",
    "media",
    "assets",
    "images",
    "fonts",
    ".git",
    ".idea",
    ".vscode",
    ".vs",
    ".DS_Store",
    "Thumbs.db",
}


# Specific extensions to skip, even if they might otherwise be considered text files.
# This includes minified files, map files, and other generated or temporary files.
SKIP_EXTENSIONS = {
    ".lock",
    ".min.js",
    ".map",
    ".pyc",
    ".log",
    ".db",
    ".egg-info",
}

# Extensions for binary files. These should be explicitly skipped for embedding but need to be mentioned in patch.
BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
}

# Full filenames that should be processed even without an extension.
FILES_TO_PROCESS_WITHOUT_EXT = {
    "Dockerfile",
}

MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB

INSTALLATION_STATE_MAPPING = {
    "deleted": ("remove", InstallationState.REMOVED),
    "suspend": ("suspend", InstallationState.SUSPENDED),
    "unsuspend": ("activate", InstallationState.ACTIVE),
}

REPO_STATE_CHANGES = {
    "deleted": RepoState.DELETED,
    "archived": RepoState.ARCHIVED,
    "unarchived": RepoState.ACTIVE,
    "privatized": None,
    "publicized": None,
}
