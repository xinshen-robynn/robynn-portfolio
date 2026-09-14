"""Import future Photography, Poster and VR projects and rebuild public content.

Usage: python3 scripts/update_content.py '/path/to/portfolio asset'
Requires Pillow. Video import additionally requires ffmpeg (or FFMPEG env).
The script never edits the source asset folder or publishes the website.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
IMAGE_TYPES = {'.jpg', '.jpeg', '.png', '.webp'}
VIDEO_TYPES = {'.mp4', '.mov', '.webm'}


def public_data(value):
    if isinstance(value, dict):
        return {k: public_data(v) for k, v in value.items() if k not in {'sourceFolder', 'sourceFolders'}}
    if isinstance(value, list):
        return [public_data(v) for v in value]
    return value


def build(data):
    from PIL import Image
    target = ROOT / 'dist/projects.js'
    output = public_data(data)
    def add_video_formats(value):
        if isinstance(value, dict):
            if str(value.get('src', '')).endswith('.mp4'):
                webm = str(Path(value['src']).with_suffix('.webm'))
                if (ROOT / 'dist' / webm).exists():
                    value['webm'] = webm
            for child in list(value.values()):
                add_video_formats(child)
        elif isinstance(value, list):
            for child in value:
                add_video_formats(child)
    add_video_formats(output)
    output['dimensions'] = {}
    for image_path in (ROOT / 'dist/assets').rglob('*.webp'):
        with Image.open(image_path) as image:
            output['dimensions'][str(image_path.relative_to(ROOT / 'dist'))] = list(image.size)
    target.write_text('window.PORTFOLIO = ' + json.dumps(output, ensure_ascii=False) + ';\n')


def import_category(category, source):
    from PIL import Image, ImageOps
    folders = [source / name for name in category['sourceFolders'] if (source / name).is_dir()]
    # Aliases can point to the same folder on a case-insensitive filesystem.
    unique = []
    for folder in folders:
        if not any(folder.samefile(other) for other in unique):
            unique.append(folder)
    for folder in unique:
        candidates = [folder] + sorted(p for p in folder.iterdir() if p.is_dir())
        for group in candidates:
            files = sorted(p for p in group.iterdir() if p.suffix.lower() in IMAGE_TYPES | VIDEO_TYPES)
            if not files:
                continue
            relative = str(group.relative_to(source))
            slug = category['id'] + '-' + hashlib.sha256(relative.encode()).hexdigest()[:10]
            dest = ROOT / 'dist/assets' / slug
            dest.mkdir(parents=True, exist_ok=True)
            images, videos = [], []
            for file in files:
                fingerprint = hashlib.sha256(file.read_bytes()).hexdigest()[:16]
                if file.suffix.lower() in IMAGE_TYPES:
                    output = dest / (fingerprint + '.webp')
                    if not output.exists():
                        image = ImageOps.exif_transpose(Image.open(file)).convert('RGB')
                        image.thumbnail((2000, 2000))
                        image.save(output, 'WEBP', quality=87, method=6)
                    images.append(str(output.relative_to(ROOT / 'dist')))
                else:
                    ffmpeg = os.environ.get('FFMPEG') or shutil.which('ffmpeg')
                    if not ffmpeg:
                        raise RuntimeError('Video import requires ffmpeg. Set FFMPEG to its path.')
                    output, poster = dest / (fingerprint + '.mp4'), dest / (fingerprint + '.webp')
                    if not output.exists():
                        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(file),
                            '-map', '0:v:0', '-map', '0:a:0?', '-vf', 'scale=1280:1280:force_original_aspect_ratio=decrease:force_divisible_by=2',
                            '-c:v', 'libx264', '-crf', '26', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '96k',
                            '-movflags', '+faststart', str(output)], check=True)
                    if output.stat().st_size > 24 * 1024 * 1024:
                        raise RuntimeError(f'Video needs a smaller web export: {file.name}')
                    webm = output.with_suffix('.webm')
                    if not webm.exists():
                        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(output),
                            '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '36', '-deadline', 'realtime',
                            '-cpu-used', '6', '-row-mt', '1', '-c:a', 'libopus', '-b:a', '64k', str(webm)], check=True)
                    if not poster.exists():
                        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(output),
                            '-frames:v', '1', str(poster)], check=True)
                    videos.append({'src': str(output.relative_to(ROOT / 'dist')), 'poster': str(poster.relative_to(ROOT / 'dist')),
                                   'title': {'en': file.stem, 'zh': file.stem}})
            metadata = group / 'project.json'
            info = json.loads(metadata.read_text()) if metadata.exists() else {}
            project = next((p for p in category['projects'] if p['id'] == slug), {'id': slug})
            project.update({'sourceFolder': relative, 'title': {'en': group.name, 'zh': group.name},
                            'date': {'en': '', 'zh': ''}, 'discipline': {'en': category['en'], 'zh': category['zh']},
                            'description': {'en': '', 'zh': ''}, 'role': {'en': '', 'zh': ''}, **info})
            project['id'] = slug
            project['rows'] = [images[i:i+2] for i in range(0, len(images), 2)]
            project['videos'] = videos
            if not any(p['id'] == slug for p in category['projects']):
                category['projects'].append(project)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('asset_folder', nargs='?')
    args = parser.parse_args()
    path = ROOT / 'content/projects.json'
    data = json.loads(path.read_text())
    if args.asset_folder:
        source = Path(args.asset_folder).expanduser().resolve()
        if not source.is_dir():
            parser.error('Asset folder does not exist')
        for category in data['categories']:
            if category.get('sourceFolders'):
                import_category(category, source)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    build(data)
    print('Updated', sum(len(c['projects']) for c in data['categories']), 'projects')
