# -*- mode: python ; coding: utf-8 -*-

hidden = [
    "orchestra",
    "livehub",
    "liveclient",
    "attach",
    "skills",
    "share",
    "source_loop",
    "workspace",
    "codework",
    "boundary",
]

a = Analysis(
    ["scripts/app.py"],
    pathex=["scripts"],
    binaries=[],
    datas=[
        ("web", "web"),
        ("scripts/open_tunnel.ps1", "scripts"),
    ],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Team Code Link",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)
