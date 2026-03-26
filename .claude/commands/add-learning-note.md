Create a new learning note from the template at `docs/templates/learning-note.md`.

Arguments: $ARGUMENTS
Format: `<slug> <title>`
The slug is the first word. The title is everything after the first word.
Examples: `drizzle-orm-basics Drizzle ORM Basics`, `docker-multistage-builds Docker Multi-Stage Builds`

Steps:
1. Parse $ARGUMENTS to extract the slug (first word) and title (remaining words).
2. Construct the file path: `docs/learning/<slug>.md`
3. Check if a file already exists at that path. If it does, tell the user and stop — do not overwrite existing notes.
4. Read `docs/templates/learning-note.md`.
5. Create the new file at the constructed path. Fill in:
   - `topic` → the slug
   - `date` → today's date in YYYY-MM-DD format
   - The title heading → the provided title
6. Confirm the file was created and show the full path.
