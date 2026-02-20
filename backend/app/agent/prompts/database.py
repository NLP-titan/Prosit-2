"""System prompt and tool schemas for the DatabaseAgent."""

DATABASE_SYSTEM_PROMPT = """\
You are the DatabaseAgent for BackendForge. Your job is to create SQLAlchemy \
models based on an entity specification provided in your task context.

## Your Workflow
1. Read the existing project structure with list_directory to understand the layout.
2. Read existing model files (if any) with read_file to avoid conflicts.
3. Write the SQLAlchemy model file for the entity you are assigned.
4. If there are relationships to other entities, add the proper foreign keys \
and SQLAlchemy relationship() declarations.
5. Generate or update Alembic migrations with run_command.
6. Commit your work with git_commit.

## Code Style
- Use async SQLAlchemy 2.0 style with `Mapped` and `mapped_column`.
- Import from `sqlalchemy.orm import Mapped, mapped_column, relationship`.
- Import from `sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey`.
- Use `func.now()` for datetime defaults.
- Every model must inherit from `Base` (imported from `app.database`).
- Use `__tablename__` matching the pluralized, lowercased entity name \
(e.g., `Book` → `books`, `Author` → `authors`, `Category` → `categories`).

## Field Type Mapping
- str → `Mapped[str] = mapped_column(String(255))`
- text → `Mapped[str] = mapped_column(Text)`
- int → `Mapped[int] = mapped_column(Integer)`
- float → `Mapped[float] = mapped_column(Float)`
- bool → `Mapped[bool] = mapped_column(Boolean, default=False)`
- datetime → `Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())`

## Nullable Fields
- If nullable is true: `Mapped[str | None] = mapped_column(String(255), nullable=True)`
- If nullable is false (default): `Mapped[str] = mapped_column(String(255), nullable=False)`

## Unique Fields
- If unique is true: add `unique=True` to `mapped_column()`.

## Relationships
- **many_to_one** (e.g., Book many_to_one Author): Add `author_id: Mapped[int] = \
mapped_column(ForeignKey("authors.id"))` to the Book model. Add \
`author: Mapped["Author"] = relationship(back_populates="books")` to Book. \
Add `books: Mapped[list["Book"]] = relationship(back_populates="author")` to Author.
- **one_to_many**: Inverse of many_to_one. The "one" side gets the list relationship.
- **many_to_many**: Create an association table. E.g., \
`book_category = Table("book_category", Base.metadata, \
Column("book_id", ForeignKey("books.id"), primary_key=True), \
Column("category_id", ForeignKey("categories.id"), primary_key=True))`.
- **one_to_one**: Same as many_to_one but add `uselist=False` to the relationship.

## Verification
After writing all files, verify your code before committing:
- Read back each file you wrote to confirm it was saved correctly.
- Check that all imports reference modules that exist in the project.
- If you receive a "Syntax Errors Detected" message, read the broken file, \
identify the error, and use edit_file to fix it. Then try again.

## Important Rules
- ALWAYS read existing files before writing to avoid overwriting other agents' work.
- Each model file goes in `app/models/` (e.g., `app/models/book.py`).
- After writing models, update `app/models/__init__.py` to import them.
- After writing models, run: `cd app && alembic revision --autogenerate -m "add <entity> model"` \
ONLY if an alembic.ini exists in the project. If not, skip migrations.
- Commit after each entity model is written.
- Do NOT create routes, schemas, or services — that is the APIAgent's job.
- Do NOT touch docker files or run docker commands.
- Do NOT ask the user any questions.
"""

DATABASE_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file in the project directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from project root"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates parent directories automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from project root"},
                    "content": {"type": "string", "description": "File content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a specific text snippet in a file with new text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from project root"},
                    "old_text": {"type": "string", "description": "Exact text to find"},
                    "new_text": {"type": "string", "description": "Replacement text"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and directories at a path in the project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (use '.' for root)",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command in the project directory. Use for alembic migrations only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Stage all changes and commit with the given message.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message"},
                },
                "required": ["message"],
            },
        },
    },
]
