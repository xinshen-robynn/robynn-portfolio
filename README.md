# Xin(Robynn)Shen — Portfolio

A bilingual, static portfolio. No special motion and no third-party font or JavaScript dependencies. All displayed project text comes from the supplied descriptions, edited and translated for the web.

## Content

- `content/projects.json`: editable bilingual project records.
- `dist/`: complete standalone website and optimized media, ready for static hosting.
- `scripts/update_content.py`: regenerates `dist/projects.js` from the content records.
- `content/media.json` and `content/videos.json`: asset provenance for the initial seven projects.

## Add Photography, Poster or VR work

The asset-folder names recognized by the importer are `Photography` (or `photograph`), `Poster` (or `poster`), and `Visual Reality` (or `VR` / `vr`). Empty categories are excluded from the website and navigation. They appear once they contain a project.

Put each new project in its own subfolder, with JPG, PNG, WebP, MP4, MOV or WebM files. For titles, dates, introductions and roles, optionally include `project.json` following `content/project.example.json`. Without metadata the importer uses the folder name and leaves unknown facts blank. Alternatively, edit the content records directly after import.

Run the importer with Python and Pillow, passing the asset folder. For video imports provide ffmpeg on PATH or use the FFMPEG environment variable. The importer copies and optimizes media into this project; it never changes originals. Run without a folder argument to rebuild public data after editing the content records.

The website cannot read a visitor's or owner's Desktop. New local files need to be imported and the website republished; adding files alone does not change the hosted version.

## Preview

Serve `dist` with any static HTTP server. Language selection is kept locally in the browser. Videos use native controls, are loaded on demand and never autoplay. Online project links open separately. No private data, contact email, unsupported biography or reference portfolio imagery is included.

## Source references

Initial content was transcribed from the seven project introduction PDFs in the supplied asset folder. Project roles and dates follow those documents, including campaign-level metrics for Samsung and Needflea. The reference portfolio is used only for composition and visual direction.
