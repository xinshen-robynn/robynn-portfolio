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

## Website and category settings

Use **Website & category settings / 网站与分类** to edit the bilingual navigation and interface labels, category names, category-card role captions and covers, Home background/tagline, About portrait/bio and contact links. Category IDs remain fixed so existing links keep working. Image selectors preview an existing asset; the upload control can add a new image.

Project editing also supports role, discipline, results/awards, custom display dates (for example Present / 至今), existing-image covers, gallery selection and video posters. Editing text leaves the original image layout intact. Save creates a content backup; Build Portfolio updates the local pages and changes asset cache versions automatically. Neither action commits, pushes or publishes.
