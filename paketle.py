"""Build a shareable source/APK archive without local identities or credentials."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / 'ogun-lab-deneme.zip'
EXCLUDED = {'build', '.gradle', '.git', '__pycache__', 'private', '.venv'}
FILES = {'README.md', 'FIREBASE-KURULUM.md', 'requirements.txt', '.gitignore',
         'baslat.ps1', 'telefonla-baslat.ps1', 'BASLAT.cmd', 'TELEFONLA-BASLAT.cmd', 'ANDROID-DERLE.cmd',
         'android-derle.ps1', 'firebase_kur.py', 'paketle.py', 'ogun-deneme.apk'}
VERIFICATION = {'RESULTS.md', 'backend-tests.txt', 'price-drops.png'}

def include(path):
    relative = path.relative_to(ROOT)
    if set(relative.parts) & EXCLUDED:
        return False
    if path.name in {'local.properties', 'google-services.json', 'firebase.xml'}:
        return False
    if path.suffix in {'.pyc', '.log', '.keystore', '.jks'}:
        return False
    if len(relative.parts) == 1:
        return path.name in FILES
    if relative.parts[0] in {'server', 'web', 'tests', 'android'}:
        return True
    return relative.parts[0] == 'verification' and path.name in VERIFICATION

if __name__ == '__main__':
    with zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob('*')):
            if path.is_file() and include(path):
                archive.write(path, Path('ogun-lab') / path.relative_to(ROOT))
    with zipfile.ZipFile(OUTPUT) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        # A source checkout may not have a built APK yet.
        if (ROOT / 'ogun-deneme.apk').is_file():
            assert 'ogun-lab/ogun-deneme.apk' in names
        assert not any('/private/' in n or '/data/' in n for n in names)
    print(f'Paket hazır: {OUTPUT.name} ({len(names)} dosya)')
