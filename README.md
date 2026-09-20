# Xin(Robynn)Shen — Portfolio

## Local Portfolio Manager

For everyday project updates, double-click [`manager/start.command`](manager/start.command) in Finder. The local Manager can edit existing projects, add projects, organize cover, gallery images and videos, rebuild the portfolio, and open a local preview. It does not commit, push, or deploy anything.

The source of truth remains `content/projects.json`. Generated pages are rebuilt into `dist/` through the existing scripts. See [`manager/README.md`](manager/README.md) for the editing flow.

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

## Third edition: page navigation

The site uses independent static HTML pages. The fixed sidebar exposes Creative, Interactive and Stills, and expands only the current category's subcategories. Each project has its own shareable page, with a persistent description and a right-hand media viewer. Images and films switch in place; arrow controls browse media groups, while previous/next project links navigate between projects in the same subcategory. Project totals are not displayed.

- `templates/page.html`: shared page shell.
- `scripts/build_pages.py`: generates home, About, category and project HTML pages.
- `content/projects.json`: includes page imagery, bilingual About copy, social links, and each project's `section`.
- Recognized project sections: `creative-direction`, `production`, `vibecoding`, `mixed-reality`, `photography`, `poster`.
- `scripts/update_content.py` also generates HTML pages, including routes for newly imported work. Photography, Poster and VR imports appear under the appropriate Stills or Interactive subcategory. Empty subcategories display a short coming-soon message.

At normal desktop sizes, project text and media share one viewport. Short screens and text enlargement allow the text column to scroll for accessibility. On mobile, the sidebar becomes a sticky menu and the content stacks vertically to keep reading and controls comfortable.

The original page photographs are in the supplied `PageAsset` folder. Optimized website copies omit the originals' metadata. The About biography is a draft based only on the work already provided.

## Fourth edition: full-background home

The home photograph fills the entire canvas beside the sidebar. White text sits above the image, and only the home page is locked to the viewport. The mobile navigation overlays the home canvas when opened. All category, About and project-page scrolling behavior remains unchanged.
