pkgname=dictate
pkgver=1.0.0
pkgrel=1
pkgdesc="Toggle-style local dictation for Linux: hotkey, whisper.cpp server/CLI, types into the focused window (KDE Wayland native)"
arch=(any)
url="https://github.com/ffschrattenecker/whisper-dictate"
license=(MIT)
depends=(python pipewire libnotify)
optdepends=(
  'wl-clipboard: clipboard injector fallback'
  'python-huggingface-hub: hf command for the model downloads in the README'
)
source=("whisper-dictate::git+https://github.com/ffschrattenecker/whisper-dictate.git#tag=v$pkgver")
sha256sums=('SKIP')

package() {
  cd "$srcdir/whisper-dictate"
  install -Dm755 dictate "$pkgdir/usr/bin/dictate"
  install -Dm644 whisper-server.service \
    "$pkgdir/usr/lib/systemd/user/whisper-server.service"
  install -Dm644 config.example.json \
    "$pkgdir/usr/share/doc/dictate/config.example.json"
  install -Dm644 test_dictate.py \
    "$pkgdir/usr/share/doc/dictate/test_dictate.py"
  install -Dm644 README.md "$pkgdir/usr/share/doc/dictate/README.md"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/dictate/LICENSE"
}
