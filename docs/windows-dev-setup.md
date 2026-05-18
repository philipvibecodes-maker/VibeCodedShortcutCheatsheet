# Windows Development & Testing Setup

This guide sets up a **two-tier environment** for developing and testing the Windows backend of Shortcut Cheatsheet from an Ubuntu host:

1. **Tier 1 — `wenv` (Wine-based Windows Python)** for the fast inner dev loop: runs `pytest` unit tests against Windows Python, lets you import `pywin32`, catches import/type errors without leaving the editor.
2. **Tier 2 — Windows 11 VM (QEMU/KVM)** for integration tests against real Win32 window-management APIs, which Wine cannot faithfully emulate.

Use Tier 1 for 90% of development. Drop into the VM for integration tests before pushing a branch, or when debugging a Win32 API that behaves suspiciously under Wine.

---

## Tier 1 — `wenv` setup

### 1.1 Install Wine

```bash
sudo dpkg --add-architecture i386
sudo apt update
sudo apt install --install-recommends wine wine64 wine32 winetricks
```

Verify:
```bash
wine --version    # expect wine-9.x or newer
```

### 1.2 Install `wenv` into the project venv

From the project root:
```bash
venv/bin/pip install wenv
venv/bin/wenv init
```

`wenv init` downloads an embeddable Windows Python into a Wine prefix (first run takes a few minutes; ~100 MB).

### 1.3 Install project deps into the Wine-hosted Python

Create a Windows-side pip install. `wenv pip` is the Windows-Python pip:

```bash
venv/bin/wenv pip install -r requirements.txt -r requirements-dev.txt
```

This will pull `PyQt6`, `pytest`, and (when we add it) `pywin32`. If `PyQt6` fails to build under Wine, that's fine — the GUI doesn't need to launch under Wine; we only need to run headless unit tests.

### 1.4 Run unit tests through Wine

```bash
venv/bin/wenv python -m pytest tests/unit -v
```

All tests should pass. The platform dispatch will select the Windows backend (since `sys.platform == "win32"` under Wine), so this exercises the Windows code paths — import validation, `pywin32` availability, stub behavior, etc. — without leaving Linux.

### What `wenv` does NOT cover

- `EnumWindows` / `GetForegroundWindow` against real host windows — returns Wine-internal handles
- DWM cloaking, full-screen detection, multi-monitor work-area calculations
- Qt window positioning under Wine's window manager
- End-to-end app launch / user interaction

→ Everything above belongs in the Tier 2 VM.

---

## Tier 2 — Windows 11 VM via QEMU/KVM

### 2.1 Install the virtualization stack

```bash
sudo apt install qemu-kvm libvirt-daemon-system libvirt-clients \
                 virt-manager ovmf bridge-utils
sudo usermod -aG libvirt,kvm $USER
# Log out and back in for group membership to take effect
```

Verify KVM acceleration:
```bash
kvm-ok                # expect "KVM acceleration can be used"
lsmod | grep kvm      # expect kvm_intel or kvm_amd loaded
```

### 2.2 Obtain Windows 11

**Recommended:** Microsoft's free pre-configured **Windows 11 Dev VM** image:
- URL: https://developer.microsoft.com/en-us/windows/downloads/virtual-machines/
- Ships with Visual Studio, WSL, 90-day resettable license
- Download is ~20 GB; available as VMware / VirtualBox / Hyper-V / Parallels — convert to qcow2 with `qemu-img convert`

**Alternative:** Official Windows 11 ISO:
- URL: https://www.microsoft.com/software-download/windows11
- Requires manual install (~30 min) and a license key for long-term use

### 2.3 Provision the VM

Open `virt-manager` → New VM → Local install media (ISO) or Import existing disk image.

Recommended specs:
- 4 vCPUs, 8 GB RAM
- 60 GB qcow2 disk
- Firmware: **UEFI** (required for Win11)
- Chipset: Q35
- NIC: virtio
- Disk bus: virtio-scsi
- Display: Spice with QXL (or VirGL)
- Enable **TPM 2.0** (swtpm) — Win11 requirement

### 2.4 First-boot setup (inside the VM)

1. Complete Windows OOBE.
2. Install Python 3.12+ from https://www.python.org/downloads/windows/ — **check "Add Python to PATH"**.
3. Install Git from https://git-scm.com/download/win.
4. Install PowerShell 7 (optional, nicer terminal).
5. Clone the repo:
   ```powershell
   git clone <your-remote> C:\dev\VibeCodedShortcutCheatsheet
   cd C:\dev\VibeCodedShortcutCheatsheet
   python -m venv venv
   venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt
   ```
6. **Snapshot the VM now** (virt-manager → View → Snapshots → Take Snapshot). Name it `clean-dev`. This is your fast-reset baseline.

### 2.5 Running tests in the VM

```powershell
venv\Scripts\python -m pytest tests\unit -v
venv\Scripts\python -m pytest tests\integration -v -m integration
venv\Scripts\python main.py
```

### 2.6 Syncing code between host and VM

Pick one:

- **Git push/pull** (recommended): work on a feature branch on the host, push, pull in the VM. Most portable, keeps history clean.
- **virtiofs shared folder**: add a filesystem device in virt-manager XML pointing at the repo root. Fast but Windows virtiofs drivers have sharp edges.
- **Samba share from the host**: lowest friction if you already have Samba configured.

---

## When to use which tier

| Situation | Tier |
|-----------|------|
| Editing Windows backend code | Tier 1 |
| Running `pytest tests/unit` | Tier 1 |
| Checking that `pywin32` imports cleanly | Tier 1 |
| Testing `EnumWindows` / `GetForegroundWindow` behavior | Tier 2 |
| Testing `get_work_area()` / multi-monitor math | Tier 2 |
| Testing full-screen detection | Tier 2 |
| Testing the Qt window actually positioning/pinning correctly | Tier 2 |
| End-to-end smoke test before opening a PR | Tier 2 |

---

## Troubleshooting

**`wenv init` hangs or fails to download Python** — check network; try `WENV_ARCH=win64 wenv init` explicitly.

**`pywin32` install fails under wenv** — known to be flaky under Wine. You can `pip install --only-binary :all: pywin32` or just skip installing it under wenv and rely on the Windows VM for anything that actually imports `win32gui` at runtime (the stub modules should still import fine).

**VM won't boot / TPM error** — install `swtpm swtpm-tools` and ensure the VM has a TPM 2.0 device attached.

**KVM not available in the VM host (nested virt)** — if this Ubuntu host is itself a VM, nested virtualization must be enabled at the hypervisor level; otherwise QEMU falls back to TCG emulation and performance will be poor.
