# Local Portfolio Manager

This local-only editor reads and updates `content/projects.json`, stores new web-ready images in `dist/assets/<project-id>/`, and runs the existing build scripts.

## Open it

Double-click `start.command` in Finder. The first launch creates a project-local Python environment and installs Flask and Pillow. The Manager opens at `http://127.0.0.1:4310`; the portfolio preview runs at `http://127.0.0.1:4173`.

Keep the Terminal window open while using the Manager. Close that window or press Control-C to stop both local services.

## Editing flow

1. Choose an existing project or create a new one.
2. Edit text, cover, gallery order, videos, and optional links.
3. Click **Save**. This updates source content and keeps a local backup in `.portfolio-manager-runtime/backups/`.
4. Click **Build Portfolio**.
5. Click **Open Local Preview**.

The Manager does not run Git commands and does not publish the site.

Uploaded MP4, MOV, and WebM files are converted to browser-ready MP4 files. A poster image is generated automatically. Reordering or removing a video changes the project record but does not delete an existing media file from disk.
