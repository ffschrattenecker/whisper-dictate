# dictate

Local dictation for Arch + KDE Plasma Wayland. Press a hotkey to start
recording, press again to stop; the clip is transcribed locally and typed
into the focused window. One Python script, standard library only.

## Install and hotkey

```sh
sudo pacman -S --needed libnotify wl-clipboard
ln -s "$PWD/dictate" ~/.local/bin/dictate   # or: install -Dm755 dictate ~/.local/bin/
```

KDE: System Settings → Keyboard → Shortcuts → Add Command →
`/home/youruser/.local/bin/dictate`, assign e.g. `Meta+A`.

## ASR server

whisper.cpp (Vulkan for AMD/Intel/NVIDIA; CUDA builds work too):

```sh
cmake -B build-vulkan -DGGML_VULKAN=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build-vulkan -j --target whisper-server
install -Dm755 build-vulkan/bin/whisper-server ~/.local/bin/
# model (hf: pacman -S python-huggingface-hub)
hf download ggml-org/whisper-large-v3-turbo ggml-large-v3-turbo.bin --local-dir ~/.local/share/whisper
cp whisper-server.service ~/.config/systemd/user/
systemctl --user enable --now whisper-server
```

The model stays resident on the GPU (~30–70 ms per short clip; bigger
models like `large-v3-turbo` trade boot time and VRAM for better
punctuation). The server must be running — with it down, dictation
exits with an error.

## Config (`~/.config/dictate/config.json`, all optional)

| key | default | |
| --- | --- | --- |
| `server_url` | `http://127.0.0.1:8080` | whisper.cpp server; `""` disables |
| `language` | `auto` | ISO code, e.g. `en`; pinning is faster and fewer hallucinations |
| `prompt` | empty | initial prompt for whisper models |
| `injector` | `auto` | `auto`, `kwin`, `clipboard` |
| `type_delay_ms` | `0` | pause between characters while typing; 0 = one burst |
| `source` | empty | PipeWire node to record from; empty = default source |
| `sound_cues` | `true` | beep on start/stop |
| `replacements` | built-in | spoken phrases → characters |

Injection: KWin's `org_kde_kwin_fake_input` protocol — layout-independent,
types into terminals, doesn't touch the clipboard. Fallback: clipboard
(`wl-copy` + ctrl+v), for apps that swallow typed keys; it restores your
clipboard 0.7 s after pasting.

Spoken phrases like "asterisk" or "forward slash" become their characters
per the `replacements` map (defaults only use phrases that are never
natural words). Entries merge over the defaults; a null value removes a
trigger; say "literal <phrase>" to type it as words.

CLI: `--stop` cancels a running recording, `--file clip.wav --stdout`
prints the transcript instead of typing, `--server`/`--lang` override the
config once, `--version` prints the version.

Fixed behavior: clips under 0.3 s are discarded, short-clip hallucinations
("Thank you." on silence) are dropped, newlines are flattened to spaces,
and injections are serialized so two clips never interleave.

## Privacy and security

- **Audio stays in RAM.** Clips are recorded into `$XDG_RUNTIME_DIR` (a
  per-user 0700 tmpfs) and deleted right after transcription; raw
  dictation audio never touches the disk and cannot outlive the login.
- **Keep the server on localhost.** whisper-server has no
  authentication, and transcripts can contain anything you dictate,
  including passwords. The bundled `whisper-server.service` therefore
  pins `--host 127.0.0.1`; don't point it at the network without an
  authenticated proxy in front.
- **The clipboard injector leaks into clipboard history.** The
  transcript sits on the clipboard for under a second before the old
  content is restored, but clipboard managers (KDE Klipper etc.)
  snapshot it into permanent history the moment it is set — the restore
  cannot prevent that. Prefer `"injector": "kwin"` or disable the
  manager's history if that matters to you.
- **Transcripts pass through argv.** The clipboard injector hands the
  text to `wl-copy` as a command-line argument, so it is briefly
  visible in `/proc` to other local users (single-user machine: not a
  concern).
- **Text types into whatever window has focus when transcription
  finishes** — seconds after you press the hotkey. Switching windows
  in between (e.g. into a password field) sends the text there.

## Troubleshooting

First: `dictate --file clip.wav --stdout` — if text prints, audio and ASR
are fine and the problem is injection (the notification names the
injector). Recorder errors: `~/.cache/dictate/recorder.log`.

- **Transcribes system sounds.** Default source is a desktop-audio
  monitor (`pactl get-default-source` ends in `.monitor`). Set your mic
  as default, or pin `source`. Dictation refuses to start in that state.
- **"No text injector available".** The kwin injector needs a running
  Plasma Wayland session (`echo $WAYLAND_DISPLAY`); the clipboard
  fallback needs `wl-clipboard`. If one specific app swallows typed
  keys, force `"injector": "clipboard"`.
- **Text appears in another layout's characters.** Both injectors type
  by keysym, not keycode, so layout is irrelevant; pin `language` when
  dictating non-English text.
- **Server unreachable.** `systemctl --user status whisper-server`;
  dictation exits with an error until it is back.

Also in the repo: `test_dictate.py` (run: `python3 test_dictate.py`)
and `PKGBUILD` (`makepkg -si`). MIT, see LICENSE.
