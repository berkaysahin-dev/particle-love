"""
 Starlight Heart  -  made of particles
 pip install numpy opencv-python
 python love.py            (live window)
 python love.py --save     (writes out/love.mp4)
"""
import os
import subprocess
import sys
import time
import numpy as np
import cv2

W, H = 600, 830          # canvas
FPS = 60
SLOW = 13.5 / 11.0       # >1 = slower
DURATION = 14.0          # seconds
N = 15000                # particles
IMAGE = "love.png"
REF = "love_ref.jpg"

TOP = np.array([245, 255, 130], np.float32)    # BGR  electric cyan
MID = np.array([255, 175, 70], np.float32)     # BGR  sky blue
BOT = np.array([255, 120, 195], np.float32)    # BGR  violet
ORB = np.array([255, 120, 255], np.float32)    # BGR  pink spark


def _fit(img, interp=cv2.INTER_AREA):
    s = min((W - 40) / img.shape[1], (H - 40) / img.shape[0])
    img = cv2.resize(img, None, fx=s, fy=s, interpolation=interp)
    oy, ox = (H - img.shape[0]) // 2, (W - img.shape[1]) // 2
    return img, oy, ox


def load_lines(path):
    here = os.path.dirname(os.path.abspath(__file__))
    full = path if os.path.isabs(path) else os.path.join(here, path)
    img = cv2.imdecode(np.fromfile(full, np.uint8), cv2.IMREAD_GRAYSCALE)
    ink = (255 - img).astype(np.float32) / 255.0
    ink, oy, ox = _fit(ink, cv2.INTER_AREA)
    avg = cv2.GaussianBlur(ink, (0, 0), 3.0)
    ink = np.clip(ink * 1.35 - avg * .45, 0, 1)
    ink = np.clip((ink - .08) / .92, 0, 1) ** .85
    out = np.zeros((H, W), np.float32)
    out[oy:oy + ink.shape[0], ox:ox + ink.shape[1]] = ink
    return out


def load_ref(path):
    here = os.path.dirname(os.path.abspath(__file__))
    full = path if os.path.isabs(path) else os.path.join(here, path)
    img = cv2.imdecode(np.fromfile(full, np.uint8), cv2.IMREAD_COLOR)
    img, oy, ox = _fit(img, cv2.INTER_LANCZOS4)
    out = np.zeros((H, W, 3), np.uint8)
    out[oy:oy + img.shape[0], ox:ox + img.shape[1]] = img
    return out


def gradient(y):
    t = np.clip(y / H, 0, 1)[..., None]
    a = np.clip(t * 2, 0, 1)
    b = np.clip(t * 2 - 1, 0, 1)
    return TOP * (1 - a) + MID * a * (1 - b) + BOT * b


def ease(t):
    t = np.clip(t, 0, 1)
    return np.where(t < .5, 4 * t ** 3, 1 - (-2 * t + 2) ** 3 / 2)


def sample_targets(lines, n, rng):
    ys, xs = np.nonzero(lines > 0.25)
    w = lines[ys, xs] ** 2
    idx = rng.choice(len(xs), n, p=w / w.sum())
    return np.stack([xs[idx], ys[idx]], 1).astype(np.float32)


def sphere(n):
    i = np.arange(n) + .5
    phi = np.arccos(1 - 2 * i / n)
    th = np.pi * (1 + 5 ** .5) * i
    return np.stack([np.cos(th) * np.sin(phi),
                     np.cos(phi),
                     np.sin(th) * np.sin(phi)], 1).astype(np.float32)


def splat(canvas, pts, col, alpha):
    x = pts[:, 0].astype(np.int32)
    y = pts[:, 1].astype(np.int32)
    ok = (x >= 0) & (x < W) & (y >= 0) & (y < H) & (alpha > 0)
    idx = y[ok] * W + x[ok]
    vals = col[ok] * alpha[ok, None]
    flat = canvas.reshape(-1, 3)
    for c in range(3):
        flat[:, c] += np.bincount(idx, weights=vals[:, c], minlength=W * H)


class Love:
    def __init__(self, path=IMAGE, ref=REF, seed=7):
        rng = np.random.default_rng(seed)
        self.ref_u8 = load_ref(ref)
        self.ref_f = self.ref_u8.astype(np.float32)
        self.lines = load_lines(path)[..., None]
        self.core = (self.lines ** 1.8) * np.float32(65.0)
        self.yy = np.arange(H, dtype=np.float32)
        self.grad_y = gradient(self.yy)[:, None, :]
        self.target = sample_targets(self.lines[..., 0], N, rng)
        tx = np.clip(self.target[:, 0].astype(int), 0, W - 1)
        ty = np.clip(self.target[:, 1].astype(int), 0, H - 1)
        self.scol = np.clip(self.ref_f[ty, tx] * 1.25 + 25.0, 0, 255)
        self.ball = sphere(N)[rng.permutation(N)]
        self.ball *= (1 + rng.normal(0, .07, N).astype(np.float32))[:, None]
        self.delay = (self.target[:, 1] / H) * 1.3 + rng.random(N) * .4
        self.swirl = rng.normal(0, 60, N).astype(np.float32)
        self.tcol = gradient(self.target[:, 1])
        self.center = np.array([W / 2, H * .45], np.float32)
        self.R = 210.0
        self.ones = np.ones(N, np.float32)
        self.white = np.full((N, 3), 255, np.float32)
        self.bcol = self.white * .45 + self.tcol * .55
        self.cv = np.zeros((H, W, 3), np.float32)
        self.small = np.zeros((H // 2, W // 2, 3), np.float32)
        self.glow = np.zeros((H, W, 3), np.float32)
        g = np.zeros((H, W), np.float32)
        cx, cy = map(int, self.center)
        cv2.circle(g, (cx, cy), 18, 1.0, -1)
        self.orb_glow = cv2.GaussianBlur(g, (0, 0), 22)[..., None] * 9 * ORB

    def ball_pos(self, t, grow=1.0):
        a, tilt = t * 1.6, .35
        p = self.ball
        x = p[:, 0] * np.cos(a) + p[:, 2] * np.sin(a)
        z = -p[:, 0] * np.sin(a) + p[:, 2] * np.cos(a)
        y = p[:, 1] * np.cos(tilt) - z * np.sin(tilt)
        z = p[:, 1] * np.sin(tilt) + z * np.cos(tilt)
        xy = self.center + np.stack([x, y], 1) * self.R * grow
        depth = (z + 1.6) / 2.6
        return xy, depth

    def draw_art(self, reveal=1.0, gain=1.0):
        band, pos = 160, reveal * (H + 160)
        y = self.yy[:, None, None]
        mask = np.clip((pos - y) / band, 0, 1)
        edge = np.exp(-((pos - band * .5 - y) / 18) ** 2)
        row = (self.grad_y * mask * .95 + 255 * edge * .85) * gain
        np.multiply(self.lines, row, out=self.cv)
        self.cv += self.core * (mask * gain)

    def frame(self, t):
        # 0  open on the original scene, right away
        if t < 1.23:
            return self.ref_u8
        t -= .41

        cv = self.cv
        ones, bcol = self.ones, self.bcol

        # 1  it shatters into a spinning ball
        if t < 1.65:
            cv.fill(0)
            u = float(ease((t - .82) / .83))
            cu = float(ease((t - .82) / .35))
            xy1, d = self.ball_pos(t)
            xy = self.target * (1 - u) + xy1 * u
            col = self.scol * (1 - cu) + bcol * cu
            alpha = ones * 1.5 * (1 - u) + d * d * 1.6 * u
            splat(cv, xy, col, alpha)
            cv2.GaussianBlur(cv, (0, 0), .6, dst=cv)
            ra = max(0.0, 1.0 - float(ease((t - .82) / .18)))
            if ra > .01:
                cv += self.ref_f * ra

        # 2  the ball spins
        elif t < 3.0:
            cv.fill(0)
            xy, d = self.ball_pos(t)
            splat(cv, xy, bcol, d * d * 1.6)
            cv2.GaussianBlur(cv, (0, 0), .6, dst=cv)

        # 3  every piece flies back to its place
        elif t < 5.4:
            cv.fill(0)
            xy0, d = self.ball_pos(3.0)
            u = ease((t - 3.0 - self.delay * .7) / 1.3)
            mx = u[:, None]
            dx = self.target[:, 0] - xy0[:, 0]
            dy = self.target[:, 1] - xy0[:, 1]
            side = np.stack([-dy, dx], 1)
            side /= np.linalg.norm(side, axis=1, keepdims=True) + 1e-6
            arc = np.sin(np.pi * u)[:, None] * self.swirl[:, None] * side
            xy = xy0 * (1 - mx) + self.target * mx + arc
            col = bcol * (1 - mx) + self.tcol * mx
            splat(cv, xy, col, ones * (d * d * (1 - u) + u) * 1.5)
            cv2.GaussianBlur(cv, (0, 0), .6, dst=cv)

        # 4  the light sweeps down and the drawing lights up
        else:
            reveal = (t - 5.4) / 2.2
            fade = max(0.0, 1.0 - float(ease(reveal)))
            if fade > .01:
                cv.fill(0)
                twinkle = .6 + .4 * np.sin(t * 6 + self.swirl)
                splat(cv, self.target, self.tcol, ones * fade * twinkle * 1.4)
                cv2.GaussianBlur(cv, (0, 0), .6, dst=cv)
                particles = cv.copy()
                self.draw_art(reveal, 1.0)
                cv += particles
            else:
                self.draw_art(reveal, 1.0)

        # a spark at the center of the ball
        orb_k = np.exp(-((t - 2.6) / .6) ** 2)
        if orb_k > .01:
            cv += self.orb_glow * orb_k

        cv2.resize(cv, (W // 2, H // 2), dst=self.small,
                   interpolation=cv2.INTER_AREA)
        cv2.GaussianBlur(self.small, (0, 0), 3.5, dst=self.small)
        cv2.resize(self.small, (W, H), dst=self.glow,
                   interpolation=cv2.INTER_LINEAR)
        k = .8 - .52 * float(ease((t - 5.4) / 2.0)) if t > 1.0 else .2
        cv2.addWeighted(cv, 1.0, self.glow, k, 0.0, dst=cv)
        return cv2.convertScaleAbs(cv)

    def frames(self):
        for i in range(int(DURATION * FPS)):
            yield self.frame(i / FPS / SLOW)


if __name__ == "__main__":
    z = Love()
    if "--save" in sys.argv:
        here = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(os.path.join(here, "out"), exist_ok=True)
        out_path = os.path.join(here, "out", "love.mp4")
        ff = subprocess.Popen([
            "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
            "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-c:v", "libx264", "-preset", "slow", "-crf", "17",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path,
        ], stdin=subprocess.PIPE)
        for f in z.frames():
            ff.stdin.write(f.tobytes())
        ff.stdin.close()
        ff.wait()
    else:
        t0 = time.perf_counter()
        for i, f in enumerate(z.frames()):
            cv2.imshow("love", f)
            ms = max(1, int((t0 + (i + 1) / FPS - time.perf_counter()) * 1000))
            if cv2.waitKey(ms) == 27:
                break
        cv2.waitKey(0)
