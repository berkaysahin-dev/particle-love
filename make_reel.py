"""Renders the vertical video: the animation on the left, love.py scrolling on the right.
Output: out/love_reel.mp4 (1080x1920, 60 fps, H.264, silent)."""
import os
import re
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import love as jf  # noqa: E402

AW, AH = jf.W, jf.H

RW, RH = 1080, 1920
ART_X = 0
BAND_Y = (RH - AH) // 2
CODE_X = AW + 20
CODE_W = RW - CODE_X
LOGO = 60
LOGO_X = (RW - LOGO) // 2
LOGO_Y = BAND_Y - 100
FONT = "C:/Windows/Fonts/consola.ttf"
FS, LH = 14, 18
TAB_H = 30

# VS Code Dark+ palette (RGB)
COLORS = [
    (Token.Comment, (106, 153, 85)),
    (Token.Literal.String.Doc, (106, 153, 85)),
    (Token.Literal.String, (206, 145, 120)),
    (Token.Literal.Number, (181, 206, 168)),
    (Token.Keyword, (197, 134, 192)),
    (Token.Name.Builtin, (220, 220, 170)),
    (Token.Name.Function, (220, 220, 170)),
    (Token.Name.Class, (78, 201, 176)),
    (Token.Name.Namespace, (78, 201, 176)),
    (Token.Operator, (212, 212, 212)),
    (Token.Name, (156, 220, 254)),
]
DEFAULT = (212, 212, 212)
EDITOR_BG = (30, 30, 30)

_PY_BLUE = (
    "M7.90472 0.00013087C7.24498 0.00316295 6.61493 0.0588153 6.06056 0.15584"
    "C4.42744 0.441207 4.13093 1.0385 4.13093 2.14002V3.59479H7.99018V4.07971"
    "H4.13093H2.68259C1.56098 4.07971 0.578874 4.7465 0.271682 6.01495"
    "C-0.0826595 7.4689 -0.0983765 8.37618 0.271682 9.89434"
    "C0.546011 11.0244 1.20115 11.8296 2.32275 11.8296H3.64965V10.0856"
    "C3.64965 8.82574 4.75178 7.71441 6.06056 7.71441H9.91531"
    "C10.9883 7.71441 11.8449 6.84056 11.8449 5.77472V2.14002"
    "C11.8449 1.10556 10.9626 0.328486 9.91531 0.15584"
    "C9.25235 0.046687 8.56447 -0.00290121 7.90472 0.00013087Z"
)
_PY_GOLD = (
    "M12.3262 4.07971V5.77472C12.3262 7.08883 11.1998 8.19488 9.9153 8.19488"
    "H6.06055C5.00466 8.19488 4.13092 9.0887 4.13092 10.1346V13.7693"
    "C4.13092 14.8037 5.04038 15.4122 6.06055 15.709"
    "C7.28217 16.0642 8.45364 16.1285 9.9153 15.709"
    "C10.8869 15.4307 11.8449 14.8708 11.8449 13.7693V12.3145H7.99017V11.8296"
    "H11.8449H13.7746C14.8962 11.8296 15.3141 11.0558 15.7042 9.89434"
    "C16.1071 8.69865 16.09 7.5488 15.7042 6.01495"
    "C15.427 4.91058 14.8976 4.07971 13.7746 4.07971H12.3262Z"
)


def _svg_poly(d_str, scale):
    tokens = re.findall(r"[MHVCZ]|-?\d*\.?\d+(?:e[-+]?\d+)?", d_str)
    pts, i, cx, cy, cmd = [], 0, 0.0, 0.0, ""
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd == "Z":
                continue
        if cmd == "M":
            cx, cy = float(tokens[i]), float(tokens[i + 1])
            i += 2
            pts.append((cx * scale, cy * scale))
        elif cmd == "H":
            cx = float(tokens[i])
            i += 1
            pts.append((cx * scale, cy * scale))
        elif cmd == "V":
            cy = float(tokens[i])
            i += 1
            pts.append((cx * scale, cy * scale))
        elif cmd == "C":
            x1, y1, x2, y2, x3, y3 = map(float, tokens[i:i + 6])
            i += 6
            for k in range(1, 17):
                t = k / 16.0
                a, b, c, e = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
                pts.append(((a * cx + b * x1 + c * x2 + e * x3) * scale,
                            (a * cy + b * y1 + c * y2 + e * y3) * scale))
            cx, cy = x3, y3
    return pts


def python_logo(size=LOGO):
    s = 4
    sc = size * s / 16.0
    mb = Image.new("L", (size * s, size * s), 0)
    ImageDraw.Draw(mb).polygon(_svg_poly(_PY_BLUE, sc), fill=255)
    ImageDraw.Draw(mb).ellipse([5.09 * sc, 1.17 * sc, 6.54 * sc, 2.62 * sc], fill=0)

    mg = Image.new("L", (size * s, size * s), 0)
    ImageDraw.Draw(mg).polygon(_svg_poly(_PY_GOLD, sc), fill=255)
    ImageDraw.Draw(mg).ellipse([9.43 * sc, 13.28 * sc, 10.88 * sc, 14.74 * sc], fill=0)

    yy, xx = np.mgrid[0:size * s, 0:size * s].astype(np.float32) / (size * s)
    u = np.clip((xx + yy) * .55, 0, 1)[..., None]
    blue = np.array([90, 159, 212], np.float32) * (1 - u) + np.array([48, 105, 152], np.float32) * u
    gold = np.array([255, 232, 115], np.float32) * (1 - u) + np.array([255, 212, 59], np.float32) * u
    ab = (np.array(mb, np.float32) / 255.0)[..., None]
    ag = (np.array(mg, np.float32) / 255.0)[..., None]
    out = cv2.resize((blue * ab + gold * ag)[:, :, ::-1], (size, size), interpolation=cv2.INTER_AREA)
    return np.clip(out, 0, 255).astype(np.uint8)


def color_for(tok):
    for t, c in COLORS:
        if tok in t:
            return c
    return DEFAULT


def render_code(src):
    font = ImageFont.truetype(FONT, FS)
    lines = src.splitlines()
    gutter = 40
    img = Image.new("RGB", (CODE_W, len(lines) * LH + 40), EDITOR_BG)
    d = ImageDraw.Draw(img)
    x, y, line = gutter, 6, 1
    d.text((4, y), f"{line:>3}", font=font, fill=(110, 118, 129))
    for tok, val in lex(src, PythonLexer()):
        parts = val.split("\n")
        for k, part in enumerate(parts):
            if k:
                line += 1
                x, y = gutter, y + LH
                d.text((4, y), f"{line:>3}", font=font, fill=(110, 118, 129))
            if part:
                d.text((x, y), part, font=font, fill=color_for(tok))
                x += font.getlength(part)
    return np.array(img)[:, :, ::-1].copy()  # BGR


def editor_chrome():
    font = ImageFont.truetype(FONT, 13)
    bar = Image.new("RGB", (CODE_W, TAB_H), (37, 37, 38))
    d = ImageDraw.Draw(bar)
    d.rectangle([0, 0, 140, TAB_H], fill=EDITOR_BG)
    d.rectangle([0, 0, 110, 1], fill=(0, 122, 204))
    d.text((12, 8), "love.py", font=font, fill=(230, 230, 230))
    d.ellipse([122, 12, 128, 18], fill=(230, 230, 230))
    return np.array(bar)[:, :, ::-1].copy()


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)
    src = open("love.py", encoding="utf-8").read()
    code = render_code(src)
    chrome = editor_chrome()
    logo = python_logo()
    view_h = AH - TAB_H
    scroll_max = max(0, code.shape[0] - view_h)

    os.makedirs("out", exist_ok=True)
    out = os.path.join("out", "love_reel.mp4")
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{RW}x{RH}", "-r", str(jf.FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", out,
    ], stdin=subprocess.PIPE)

    j = jf.Love()
    total = int(jf.DURATION * jf.FPS)
    for i, art in enumerate(j.frames()):
        t = i / jf.FPS
        frame = np.zeros((RH, RW, 3), np.uint8)
        frame[LOGO_Y:LOGO_Y + LOGO, LOGO_X:LOGO_X + LOGO] = logo
        frame[BAND_Y:BAND_Y + AH, ART_X:ART_X + AW] = art
        p = float(jf.ease((t - .3) / (jf.DURATION - 1.5)))
        off = int(p * scroll_max)
        panel = frame[BAND_Y:BAND_Y + AH, CODE_X:CODE_X + CODE_W]
        panel[:TAB_H] = chrome
        panel[TAB_H:] = code[off:off + view_h]
        ff.stdin.write(frame.tobytes())
        if i % 60 == 0:
            print(f"{i}/{total}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("saved", out, "exit", ff.returncode)


if __name__ == "__main__":
    main()
