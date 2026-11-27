import math
import random
from dataclasses import dataclass
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from settings import AppSettings


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    size: float
    alpha: float
    phase: float
    spin: float
    spin_speed: float
    kind: int
    color: QColor


@dataclass
class Splash:
    x: float
    y: float
    radius: float
    max_radius: float
    alpha: float


@dataclass
class ShootingStar:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float


@dataclass
class TreeItem:
    x: float
    scale: float
    sway: float
    sway_vel: float
    phase: float
    ornaments: list[tuple[float, float, QColor]]


@dataclass
class SnowmanItem:
    x: float
    scale: float
    wobble: float
    wobble_vel: float
    scarf_color: QColor
    hat_color: QColor


@dataclass
class ExhaustPuff:
    x: float
    y: float
    vx: float
    vy: float
    r: float
    alpha: float


@dataclass
class BulldozerState:
    x: float
    dir: int
    speed: float
    wheel_phase: float
    exhaust_timer: float


class WeatherEngine:
    """Simulates and renders all 6 KoiArt seasonal/weather effects + snow drifts + holiday lights + trees + snowmen + bulldozer."""

    def __init__(self, width: int, height: int):
        self.width = max(1, width)
        self.height = max(1, height)
        self.taskbar_y = self.height - 48
        self.window_tops: list[tuple[int, int, int]] = []

        self.particles: list[Particle] = []
        self.splashes: list[Splash] = []
        self.shooting_stars: list[ShootingStar] = []

        # Snow drift heightfield along the taskbar (sampled every 4 px)
        self.bin_w = 4
        self.num_bins = max(1, (self.width // self.bin_w) + 2)
        self.taskbar_drift = [0.0] * self.num_bins

        # Per-window-top snow accumulation (keyed by (l, r, y) quantized)
        self.window_drifts: dict[tuple[int, int, int], list[float]] = {}

        # Scenery: Christmas trees (archa), ornaments (archa qo'g'irchoqlari), snowmen & bulldozers
        self.trees: list[TreeItem] = []
        self.snowmen: list[SnowmanItem] = []
        self.dozers: list[BulldozerState] = []
        self.exhaust: list[ExhaustPuff] = []
        self._last_tree_count = -1
        self._last_snowman_count = -1
        self._last_dozer_count = -1
        self._sync_scenery(5, 3, 1)

        # Lightning state (for rain)
        self.lightning_alpha = 0.0
        self.next_lightning = random.uniform(5.0, 14.0)

        # Wind gust state
        self.time = 0.0
        self.last_effect = ""
        self.prev_cursor: tuple[float, float] | None = None

    def _sync_scenery(self, tree_count: int, snowman_count: int, dozer_count: int) -> None:
        if tree_count != self._last_tree_count:
            self._last_tree_count = tree_count
            ornament_palette = [
                QColor(255, 70, 85),
                QColor(255, 210, 60),
                QColor(70, 200, 255),
                QColor(255, 105, 210),
                QColor(115, 240, 140),
            ]
            self.trees = []
            for idx in range(max(0, tree_count)):
                frac = (idx + 0.5) / max(1, tree_count)
                tx = self.width * (0.06 + 0.88 * frac)
                sc = 0.85 + (idx % 3) * 0.14
                orns = [
                    (-10.0, -48.0, ornament_palette[(idx + 0) % len(ornament_palette)]),
                    (9.0, -44.0, ornament_palette[(idx + 1) % len(ornament_palette)]),
                    (-16.0, -30.0, ornament_palette[(idx + 2) % len(ornament_palette)]),
                    (5.0, -32.0, ornament_palette[(idx + 3) % len(ornament_palette)]),
                    (17.0, -26.0, ornament_palette[(idx + 4) % len(ornament_palette)]),
                    (-22.0, -14.0, ornament_palette[(idx + 1) % len(ornament_palette)]),
                    (0.0, -16.0, ornament_palette[(idx + 0) % len(ornament_palette)]),
                    (21.0, -13.0, ornament_palette[(idx + 2) % len(ornament_palette)]),
                ]
                self.trees.append(TreeItem(tx, sc, 0.0, 0.0, idx * 1.3, orns))

        if snowman_count != self._last_snowman_count:
            self._last_snowman_count = snowman_count
            scarves = [QColor(225, 55, 65), QColor(55, 145, 235), QColor(75, 195, 115)]
            hats = [QColor(35, 40, 52), QColor(145, 45, 55), QColor(42, 58, 88)]
            self.snowmen = []
            for idx in range(max(0, snowman_count)):
                frac = (idx + 0.5) / max(1, snowman_count)
                self.snowmen.append(
                    SnowmanItem(
                        x=self.width * (0.10 + 0.80 * frac),
                        scale=0.90 + (idx % 2) * 0.12,
                        wobble=0.0,
                        wobble_vel=0.0,
                        scarf_color=scarves[idx % len(scarves)],
                        hat_color=hats[idx % len(hats)],
                    )
                )

        if dozer_count != self._last_dozer_count:
            self._last_dozer_count = dozer_count
            target = max(0, dozer_count)
            while len(self.dozers) < target:
                idx = len(self.dozers)
                start_x = 90.0 + (idx * 220.0) % max(200.0, self.width - 180.0)
                direction = 1 if idx % 2 == 0 else -1
                speed = 56.0 + (idx % 3) * 14.0
                self.dozers.append(BulldozerState(start_x, direction, speed, idx * 1.1, idx * 0.07))
            if len(self.dozers) > target:
                self.dozers = self.dozers[:target]

    def resize(self, width: int, height: int) -> None:
        self.width = max(1, width)
        self.height = max(1, height)
        self.num_bins = max(1, (self.width // self.bin_w) + 2)
        if len(self.taskbar_drift) != self.num_bins:
            self.taskbar_drift = [0.0] * self.num_bins
        tc = max(0, self._last_tree_count)
        sc = max(0, self._last_snowman_count)
        dc = max(0, self._last_dozer_count)
        self._last_tree_count = -1
        self._last_snowman_count = -1
        self._last_dozer_count = -1
        self._sync_scenery(tc, sc, dc)

    def _target_count(self, settings: AppSettings) -> int:
        base = {
            "snow": 220,
            "sakura": 95,
            "leaves": 75,
            "rain": 260,
            "fireflies": 65,
            "starfall": 90,
        }.get(settings.effect, 120)
        return max(10, int(base * (settings.intensity / 100.0)))

    def _spawn_particle(self, settings: AppSettings, random_y: bool = False) -> Particle:
        eff = settings.effect
        sz_scale = settings.size / 50.0
        x = random.uniform(-40, self.width + 40)
        y = random.uniform(0, self.height) if random_y else random.uniform(-60, -5)

        if eff == "snow":
            depth = random.uniform(0.45, 1.35)
            size = random.uniform(2.2, 6.2) * sz_scale * depth
            return Particle(
                x=x,
                y=y,
                vx=random.uniform(-12, 12),
                vy=random.uniform(28, 72) * depth,
                size=size,
                alpha=random.uniform(0.60, 0.96),
                phase=random.uniform(0, math.tau),
                spin=random.uniform(0, 360),
                spin_speed=random.uniform(-55, 55),
                kind=random.randint(0, 2),
                color=QColor(255, 255, 255),
            )
        if eff == "sakura":
            colors = [
                QColor(255, 183, 197),
                QColor(255, 209, 220),
                QColor(250, 160, 185),
                QColor(255, 228, 235),
            ]
            return Particle(
                x=x,
                y=y,
                vx=random.uniform(-15, 25),
                vy=random.uniform(32, 68),
                size=random.uniform(6.0, 12.0) * sz_scale,
                alpha=random.uniform(0.7, 0.95),
                phase=random.uniform(0, math.tau),
                spin=random.uniform(0, 360),
                spin_speed=random.uniform(-110, 110),
                kind=0,
                color=random.choice(colors),
            )
        if eff == "leaves":
            colors = [
                QColor(235, 110, 35),
                QColor(210, 60, 30),
                QColor(240, 165, 35),
                QColor(175, 75, 35),
                QColor(220, 130, 30),
            ]
            return Particle(
                x=x,
                y=y,
                vx=random.uniform(-20, 30),
                vy=random.uniform(42, 90),
                size=random.uniform(8.0, 15.0) * sz_scale,
                alpha=random.uniform(0.75, 0.98),
                phase=random.uniform(0, math.tau),
                spin=random.uniform(0, 360),
                spin_speed=random.uniform(-140, 140),
                kind=random.randint(0, 1),
                color=random.choice(colors),
            )
        if eff == "rain":
            return Particle(
                x=random.uniform(-100, self.width + 100),
                y=y,
                vx=0.0,
                vy=random.uniform(480, 780),
                size=random.uniform(14.0, 26.0) * sz_scale,
                alpha=random.uniform(0.28, 0.62),
                phase=0.0,
                spin=0.0,
                spin_speed=0.0,
                kind=0,
                color=QColor(185, 220, 255),
            )
        if eff == "fireflies":
            colors = [
                QColor(255, 235, 115),
                QColor(195, 255, 110),
                QColor(255, 200, 90),
            ]
            return Particle(
                x=random.uniform(0, self.width),
                y=random.uniform(40, self.taskbar_y - 20),
                vx=random.uniform(-22, 22),
                vy=random.uniform(-16, 16),
                size=random.uniform(3.0, 6.5) * sz_scale,
                alpha=random.uniform(0.3, 1.0),
                phase=random.uniform(0, math.tau),
                spin=0.0,
                spin_speed=random.uniform(1.5, 3.5),
                kind=0,
                color=random.choice(colors),
            )
        # starfall
        return Particle(
            x=random.uniform(0, self.width),
            y=random.uniform(0, self.height * 0.72),
            vx=0.0,
            vy=0.0,
            size=random.uniform(1.4, 3.2) * sz_scale,
            alpha=random.uniform(0.3, 0.95),
            phase=random.uniform(0, math.tau),
            spin=0.0,
            spin_speed=random.uniform(1.2, 3.8),
            kind=random.randint(0, 1),
            color=random.choice([QColor(255, 255, 255), QColor(210, 230, 255), QColor(255, 240, 205)]),
        )

    def _sync_effect(self, settings: AppSettings) -> None:
        if settings.effect != self.last_effect:
            self.particles.clear()
            self.splashes.clear()
            self.shooting_stars.clear()
            self.lightning_alpha = 0.0
            if settings.effect != "snow":
                self.taskbar_drift = [0.0] * self.num_bins
                self.window_drifts.clear()
            self.last_effect = settings.effect

        target = self._target_count(settings)
        while len(self.particles) < target:
            self.particles.append(self._spawn_particle(settings, random_y=True))
        if len(self.particles) > target:
            self.particles = self.particles[:target]

    def _smooth_drift(self, arr: list[float], max_h: float, melt_rate: float, dt: float) -> None:
        n = len(arr)
        if n < 3:
            return
        # Gentle slumping (diffusion) + slow melt
        for i in range(1, n - 1):
            avg = (arr[i - 1] + arr[i] * 2.0 + arr[i + 1]) * 0.25
            arr[i] = max(0.0, min(max_h, avg - melt_rate * dt))
        arr[0] = max(0.0, arr[0] - melt_rate * dt)
        arr[-1] = max(0.0, arr[-1] - melt_rate * dt)

    def _plow_cursor(self, cursor: tuple[float, float], settings: AppSettings) -> None:
        if not settings.mouse_interact or settings.effect != "snow":
            self.prev_cursor = cursor
            return
        cx, cy = cursor
        if self.prev_cursor is None:
            self.prev_cursor = cursor
            return
        px, py = self.prev_cursor
        dx = cx - px
        dy = cy - py
        speed = math.hypot(dx, dy)
        self.prev_cursor = cursor
        if speed < 3.0:
            return

        # Scatter nearby flakes
        radius = 65.0
        r2 = radius * radius
        for p in self.particles:
            ddx = p.x - cx
            ddy = p.y - cy
            d2 = ddx * ddx + ddy * ddy
            if 1.0 < d2 < r2:
                dist = math.sqrt(d2)
                push = (1.0 - dist / radius) * min(220.0, speed * 5.0)
                p.vx += (ddx / dist) * push * 0.15 + dx * 1.2
                p.vy += (ddy / dist) * push * 0.1 - abs(dy) * 0.4

        # Plow taskbar drift if cursor is near taskbar
        if abs(cy - self.taskbar_y) <= max(36.0, settings.drift_depth * 0.6):
            idx = int(cx // self.bin_w)
            plow_r = 7
            for i in range(max(0, idx - plow_r), min(self.num_bins, idx + plow_r + 1)):
                falloff = 1.0 - abs(i - idx) / (plow_r + 1)
                self.taskbar_drift[i] = max(0.0, self.taskbar_drift[i] - 8.0 * falloff)

    def update(
        self,
        dt: float,
        settings: AppSettings,
        taskbar_y: int,
        window_tops: list[tuple[int, int, int]],
        cursor: tuple[int, int],
    ) -> None:
        self.time += dt
        self.taskbar_y = taskbar_y
        self.window_tops = window_tops
        self._sync_effect(settings)

        speed_mul = 0.35 + (settings.speed / 100.0) * 1.45
        wind_base = (settings.wind / 100.0) * 135.0
        gust = math.sin(self.time * 0.45) * 24.0 + math.sin(self.time * 1.13) * 12.0
        wind = wind_base + gust

        self._plow_cursor((float(cursor[0]), float(cursor[1])), settings)

        eff = settings.effect
        max_drift = (settings.drift_depth / 100.0) * 46.0

        # Prune stale window drifts
        if eff == "snow" and settings.pile_on_windows and max_drift > 0.5:
            active_keys = set()
            for l, r, y in window_tops:
                key = (l // 8 * 8, r // 8 * 8, y // 4 * 4)
                active_keys.add(key)
                if key not in self.window_drifts:
                    bins = max(4, (r - l) // self.bin_w)
                    self.window_drifts[key] = [0.0] * bins
            for k in list(self.window_drifts.keys()):
                if k not in active_keys:
                    del self.window_drifts[k]
        else:
            self.window_drifts.clear()

        for i, p in enumerate(self.particles):
            if eff in ("snow", "sakura", "leaves"):
                sway = math.sin(self.time * 1.6 + p.phase) * (22.0 if eff == "snow" else 42.0)
                p.vx += ((wind + sway) - p.vx) * min(1.0, dt * 2.5)
                p.x += p.vx * dt * speed_mul
                p.y += p.vy * dt * speed_mul
                p.spin += p.spin_speed * dt * speed_mul

                # Check window-top landing for snow
                landed = False
                if eff == "snow" and settings.pile_on_windows and max_drift > 0.5:
                    for key, arr in self.window_drifts.items():
                        wl, wr, wy = key
                        if wl <= p.x <= wr and wy - 4 <= p.y <= wy + 6 and p.vy > 0:
                            b = int((p.x - wl) // self.bin_w)
                            if 0 <= b < len(arr):
                                cap = max_drift * 0.72
                                arr[b] = min(cap, arr[b] + p.size * 0.85)
                                if b > 0:
                                    arr[b - 1] = min(cap, arr[b - 1] + p.size * 0.35)
                                if b + 1 < len(arr):
                                    arr[b + 1] = min(cap, arr[b + 1] + p.size * 0.35)
                                landed = True
                                break

                # Check taskbar landing
                if not landed and p.y >= self.taskbar_y:
                    if eff == "snow" and max_drift > 0.5:
                        b = max(0, min(self.num_bins - 1, int(p.x // self.bin_w)))
                        self.taskbar_drift[b] = min(max_drift, self.taskbar_drift[b] + p.size * 1.15)
                        if b > 0:
                            self.taskbar_drift[b - 1] = min(max_drift, self.taskbar_drift[b - 1] + p.size * 0.50)
                        if b + 1 < self.num_bins:
                            self.taskbar_drift[b + 1] = min(max_drift, self.taskbar_drift[b + 1] + p.size * 0.50)
                    self.particles[i] = self._spawn_particle(settings, random_y=False)
                elif landed or p.y > self.height + 20:
                    self.particles[i] = self._spawn_particle(settings, random_y=False)
                else:
                    if p.x < -50:
                        p.x = self.width + 40
                    elif p.x > self.width + 50:
                        p.x = -40

            elif eff == "rain":
                p.vx = wind * 0.65
                p.x += p.vx * dt * speed_mul
                p.y += p.vy * dt * speed_mul
                if p.y >= self.taskbar_y:
                    if random.random() < 0.32:
                        self.splashes.append(Splash(p.x, float(self.taskbar_y), 1.5, random.uniform(6, 12), 0.65))
                    self.particles[i] = self._spawn_particle(settings, random_y=False)
                elif p.x < -120:
                    p.x = self.width + 80
                elif p.x > self.width + 120:
                    p.x = -80

            elif eff == "fireflies":
                p.phase += p.spin_speed * dt
                p.vx += random.uniform(-28, 28) * dt
                p.vy += random.uniform(-22, 22) * dt
                p.vx = max(-38, min(38, p.vx))
                p.vy = max(-28, min(28, p.vy))
                p.x += (p.vx + wind * 0.12) * dt * speed_mul
                p.y += p.vy * dt * speed_mul
                if p.x < 10:
                    p.x = self.width - 15
                elif p.x > self.width - 10:
                    p.x = 15
                if p.y < 20:
                    p.vy = abs(p.vy)
                elif p.y > self.taskbar_y - 15:
                    p.vy = -abs(p.vy)

            elif eff == "starfall":
                p.phase += p.spin_speed * dt

        # Update rain splashes & lightning
        if eff == "rain":
            new_splashes: list[Splash] = []
            for s in self.splashes:
                s.radius += 28.0 * dt
                s.alpha -= 1.8 * dt
                if s.alpha > 0.02 and s.radius < s.max_radius:
                    new_splashes.append(s)
            self.splashes = new_splashes

            self.next_lightning -= dt
            if self.next_lightning <= 0:
                self.lightning_alpha = random.uniform(0.18, 0.34)
                self.next_lightning = random.uniform(6.0, 18.0)
            if self.lightning_alpha > 0:
                self.lightning_alpha = max(0.0, self.lightning_alpha - dt * 1.4)

        # Update shooting stars
        if eff == "starfall":
            if random.random() < dt * 0.45 * (settings.intensity / 65.0):
                sx = random.uniform(self.width * 0.15, self.width * 0.95)
                sy = random.uniform(20, self.height * 0.35)
                self.shooting_stars.append(
                    ShootingStar(sx, sy, random.uniform(-520, -320), random.uniform(180, 320), 0.0, random.uniform(0.55, 0.95))
                )
            alive: list[ShootingStar] = []
            for st in self.shooting_stars:
                st.life += dt
                st.x += st.vx * dt * speed_mul
                st.y += st.vy * dt * speed_mul
                if st.life < st.max_life:
                    alive.append(st)
            self.shooting_stars = alive

        # Smooth & slowly melt snow drifts
        if eff == "snow":
            self._smooth_drift(self.taskbar_drift, max_drift, melt_rate=0.12, dt=dt)
            for arr in self.window_drifts.values():
                self._smooth_drift(arr, max_drift * 0.72, melt_rate=0.15, dt=dt)

        # Update trees, snowmen & bulldozers count from settings
        self._sync_scenery(settings.tree_count, settings.snowman_count, settings.bulldozer_count)

        # Update trees & snowmen spring sway (wind + mouse brush)
        cx, cy = float(cursor[0]), float(cursor[1])
        for tr in self.trees:
            if settings.mouse_interact and abs(cx - tr.x) < 35 and self.taskbar_y - 95 <= cy <= self.taskbar_y + 10:
                tr.sway_vel += (1 if cx < tr.x else -1) * 14.0 * dt
            # Wind + spring restore
            wind_push = (wind * 0.015) - tr.sway * 18.0 - tr.sway_vel * 3.8
            tr.sway_vel += wind_push * dt
            tr.sway = max(-0.26, min(0.26, tr.sway + tr.sway_vel * dt))

        for sm in self.snowmen:
            if settings.mouse_interact and abs(cx - sm.x) < 28 and self.taskbar_y - 65 <= cy <= self.taskbar_y + 10:
                sm.wobble_vel += (1 if cx < sm.x else -1) * 16.0 * dt
            restore = -sm.wobble * 22.0 - sm.wobble_vel * 4.2
            sm.wobble_vel += restore * dt
            sm.wobble = max(-0.30, min(0.30, sm.wobble + sm.wobble_vel * dt))

        # Update bulldozers driving & plowing along the taskbar
        if settings.show_bulldozer and self.dozers:
            margin = 65.0
            for dz in self.dozers:
                dz.x += dz.dir * dz.speed * dt
                dz.wheel_phase += dz.dir * dt * 8.0
                if dz.x > self.width - margin:
                    dz.x = self.width - margin
                    dz.dir = -1
                elif dz.x < margin:
                    dz.x = margin
                    dz.dir = 1

                # Blade position in front of bulldozer
                blade_x = dz.x + dz.dir * 38.0
                if eff == "snow" and settings.drift_depth > 0:
                    b_idx = int(blade_x // self.bin_w)
                    plowed = 0.0
                    for j in range(max(0, b_idx - 4), min(self.num_bins, b_idx + 5)):
                        if self.taskbar_drift[j] > 1.5:
                            plowed += self.taskbar_drift[j]
                            self.taskbar_drift[j] = max(0.0, self.taskbar_drift[j] * 0.25)
                    # Kick up tiny snow spray when plowing deep snow
                    if plowed > 6.0 and random.random() < 0.55 and len(self.particles) < 420:
                        self.particles.append(
                            Particle(
                                x=blade_x,
                                y=float(self.taskbar_y) - 6.0,
                                vx=dz.dir * random.uniform(35, 95),
                                vy=random.uniform(-95, -40),
                                size=random.uniform(2.0, 4.0),
                                alpha=0.85,
                                phase=random.uniform(0, math.tau),
                                spin=0.0,
                                spin_speed=0.0,
                                kind=0,
                                color=QColor(255, 255, 255),
                            )
                        )

                # Exhaust puffs
                dz.exhaust_timer += dt
                if dz.exhaust_timer >= 0.22:
                    dz.exhaust_timer = 0.0
                    pipe_x = dz.x - dz.dir * 4.0
                    pipe_y = float(self.taskbar_y) - 36.0
                    self.exhaust.append(
                        ExhaustPuff(pipe_x, pipe_y, -dz.dir * random.uniform(10, 22), random.uniform(-24, -14), 3.0, 0.55)
                    )
            alive_puff: list[ExhaustPuff] = []
            for pf in self.exhaust:
                pf.x += pf.vx * dt
                pf.y += pf.vy * dt
                pf.r += 5.5 * dt
                pf.alpha -= 0.55 * dt
                if pf.alpha > 0.03:
                    alive_puff.append(pf)
            self.exhaust = alive_puff
        else:
            self.exhaust.clear()

    def _draw_drift_strip(self, painter: QPainter, x_start: float, base_y: float, heights: list[float]) -> None:
        if not heights or max(heights) < 0.8:
            return
        path = QPainterPath()
        path.moveTo(x_start, base_y + 2)
        for i, h in enumerate(heights):
            px = x_start + i * self.bin_w
            py = base_y - h
            if i == 0:
                path.lineTo(px, py)
            else:
                prev_x = x_start + (i - 1) * self.bin_w
                prev_y = base_y - heights[i - 1]
                mid_x = (prev_x + px) * 0.5
                mid_y = (prev_y + py) * 0.5
                path.quadTo(prev_x, prev_y, mid_x, mid_y)
        end_x = x_start + (len(heights) - 1) * self.bin_w
        path.lineTo(end_x, base_y + 2)
        path.closeSubpath()

        grad = QLinearGradient(0, base_y - max(heights), 0, base_y + 2)
        grad.setColorAt(0.0, QColor(255, 255, 255, 240))
        grad.setColorAt(1.0, QColor(220, 234, 248, 215))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawPath(path)

    def _draw_holiday_lights(self, painter: QPainter, settings: AppSettings) -> None:
        bulb_colors = [
            QColor(255, 75, 75),
            QColor(70, 230, 110),
            QColor(255, 210, 65),
            QColor(80, 175, 255),
            QColor(255, 110, 210),
        ]
        scale = max(0.4, settings.light_size / 50.0)
        spacing = max(24, int(46 * (0.7 + 0.3 * scale)))
        wire_pen = QPen(QColor(35, 55, 40, 200), 2.0)
        painter.setPen(wire_pen)
        painter.setBrush(Qt.NoBrush)

        # Draw scalloped wire across top
        wire = QPainterPath()
        wire.moveTo(0, 4)
        for x in range(0, self.width + spacing, spacing):
            sag = (10 + 4 * math.sin(x * 0.02 + self.time * 0.9)) * scale
            wire.quadTo(x - spacing * 0.5, sag + 8, x, 4)
        painter.drawPath(wire)

        idx = 0
        glow_r = 18.0 * scale
        bulb_rx = 4.5 * scale
        bulb_ry = 6.2 * scale
        for x in range(20, self.width, spacing):
            pulse = 0.65 + 0.35 * math.sin(self.time * 2.4 + idx * 0.9)
            c = QColor(bulb_colors[idx % len(bulb_colors)])
            by = (13 + 3 * math.sin(x * 0.02 + self.time * 0.9)) * (0.65 + 0.35 * scale)

            glow = QRadialGradient(x, by, glow_r)
            gc = QColor(c)
            gc.setAlpha(int(120 * pulse))
            glow.setColorAt(0.0, gc)
            glow.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QPointF(x, by), glow_r, glow_r)

            c.setAlpha(int(235 * (0.55 + 0.45 * pulse)))
            painter.setBrush(QBrush(c))
            painter.drawEllipse(QPointF(x, by), bulb_rx, bulb_ry)
            idx += 1

    def render(self, painter: QPainter, settings: AppSettings) -> None:
        painter.setRenderHint(QPainter.Antialiasing, True)
        eff = settings.effect

        if eff == "rain" and self.lightning_alpha > 0.005:
            painter.fillRect(0, 0, self.width, self.height, QColor(225, 240, 255, int(255 * self.lightning_alpha)))

        # Draw particles
        for p in self.particles:
            if eff == "snow":
                c = QColor(p.color)
                c.setAlphaF(p.alpha)
                draw_round = (
                    settings.snowflake_shape == "round"
                    or (settings.snowflake_shape == "mixed" and p.kind == 0)
                )
                if draw_round:
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(c))
                    painter.drawEllipse(QPointF(p.x, p.y), p.size * 0.85, p.size * 0.85)
                else:
                    # 6-pointed star-shaped crystal snowflake
                    painter.save()
                    painter.translate(p.x, p.y)
                    painter.rotate(p.spin)
                    r = p.size * 1.45
                    painter.setPen(QPen(c, max(1.0, p.size * 0.24), Qt.SolidLine, Qt.RoundCap))
                    for k in range(3):
                        ang = k * (math.pi / 3.0)
                        dx = r * math.cos(ang)
                        dy = r * math.sin(ang)
                        painter.drawLine(QPointF(-dx, -dy), QPointF(dx, dy))
                    if p.kind == 2 and r >= 4.0:
                        # Tiny crystal side-branches
                        painter.setPen(QPen(c, max(0.8, p.size * 0.17), Qt.SolidLine, Qt.RoundCap))
                        for k in range(6):
                            ang = k * (math.pi / 3.0)
                            bx = r * 0.58 * math.cos(ang)
                            by = r * 0.58 * math.sin(ang)
                            for side in (-0.55, 0.55):
                                sx = bx + r * 0.32 * math.cos(ang + side)
                                sy = by + r * 0.32 * math.sin(ang + side)
                                painter.drawLine(QPointF(bx, by), QPointF(sx, sy))
                    painter.restore()

            elif eff in ("sakura", "leaves"):
                painter.save()
                painter.translate(p.x, p.y)
                painter.rotate(p.spin)
                c = QColor(p.color)
                c.setAlphaF(p.alpha)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(c))
                if eff == "sakura":
                    painter.drawEllipse(QRectF(-p.size * 0.5, -p.size * 0.3, p.size, p.size * 0.6))
                else:
                    path = QPainterPath()
                    s = p.size * 0.55
                    path.moveTo(0, -s)
                    path.quadTo(s * 0.9, 0, 0, s)
                    path.quadTo(-s * 0.9, 0, 0, -s)
                    painter.drawPath(path)
                painter.restore()

            elif eff == "rain":
                c = QColor(p.color)
                c.setAlphaF(p.alpha)
                painter.setPen(QPen(c, 1.3))
                dx = (p.vx / max(1.0, p.vy)) * p.size
                painter.drawLine(QPointF(p.x, p.y), QPointF(p.x - dx, p.y - p.size))

            elif eff == "fireflies":
                pulse = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(p.phase))
                r = p.size * 3.8
                grad = QRadialGradient(p.x, p.y, r)
                c0 = QColor(p.color)
                c0.setAlphaF(min(1.0, p.alpha * pulse))
                c1 = QColor(p.color)
                c1.setAlpha(0)
                grad.setColorAt(0.0, c0)
                grad.setColorAt(0.35, QColor(c0.red(), c0.green(), c0.blue(), int(c0.alpha() * 0.45)))
                grad.setColorAt(1.0, c1)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(grad))
                painter.drawEllipse(QPointF(p.x, p.y), r, r)

            elif eff == "starfall":
                twinkle = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(p.phase))
                c = QColor(p.color)
                c.setAlphaF(p.alpha * twinkle)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(c))
                painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)

        # Rain splashes
        if eff == "rain":
            for s in self.splashes:
                c = QColor(200, 230, 255, int(255 * s.alpha))
                painter.setPen(QPen(c, 1.1))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(s.x, s.y - 1), s.radius, s.radius * 0.35)

        # Shooting stars
        if eff == "starfall":
            for st in self.shooting_stars:
                prog = st.life / st.max_life
                alpha = math.sin(prog * math.pi)
                tail_x = st.x - st.vx * 0.14
                tail_y = st.y - st.vy * 0.14
                grad = QLinearGradient(st.x, st.y, tail_x, tail_y)
                grad.setColorAt(0.0, QColor(255, 255, 255, int(245 * alpha)))
                grad.setColorAt(1.0, QColor(180, 220, 255, 0))
                painter.setPen(QPen(QBrush(grad), 2.2, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(QPointF(st.x, st.y), QPointF(tail_x, tail_y))

        # Snow drifts on windows & taskbar
        if eff == "snow" and settings.drift_depth > 0:
            if settings.pile_on_windows:
                for (wl, _, wy), arr in self.window_drifts.items():
                    self._draw_drift_strip(painter, float(wl), float(wy), arr)
            self._draw_drift_strip(painter, 0.0, float(self.taskbar_y), self.taskbar_drift)

        # Christmas trees (archa) with ornaments (archa qo'g'irchoqlari)
        if settings.show_trees:
            self._draw_trees(painter, settings)

        # Snowmen (qo'g'irchoqlar / qorbobolar)
        if settings.show_snowmen:
            self._draw_snowmen(painter)

        # Animated bulldozer plowing snow
        if settings.show_bulldozer:
            self._draw_bulldozer(painter)

        # Optional holiday lights
        if settings.holiday_lights:
            self._draw_holiday_lights(painter, settings)

    def _draw_trees(self, painter: QPainter, settings: AppSettings) -> None:
        base_y = float(self.taskbar_y)
        for tr in self.trees:
            painter.save()
            painter.translate(tr.x, base_y)
            painter.scale(tr.scale, tr.scale)
            painter.rotate(math.degrees(tr.sway))

            # Trunk
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(105, 65, 38, 240))
            painter.drawRoundedRect(QRectF(-5, -14, 10, 16), 2, 2)

            # 3 Pine tiers
            tiers = [
                (QPointF(0, -42), QPointF(-29, -10), QPointF(29, -10), QColor(20, 95, 52, 245)),
                (QPointF(0, -64), QPointF(-23, -28), QPointF(23, -28), QColor(26, 114, 62, 245)),
                (QPointF(0, -84), QPointF(-16, -48), QPointF(16, -48), QColor(34, 134, 74, 245)),
            ]
            for top, left, right, col in tiers:
                path = QPainterPath()
                path.moveTo(top)
                path.lineTo(left)
                path.quadTo(0, left.y() + 5, right.x(), right.y())
                path.closeSubpath()
                painter.setBrush(col)
                painter.drawPath(path)

                # Snow cap on bough tip if snow effect is active
                if settings.effect == "snow" and settings.drift_depth > 10:
                    snow_cap = QPainterPath()
                    snow_cap.moveTo(top)
                    snow_cap.lineTo(top.x() - (top.x() - left.x()) * 0.45, top.y() + (left.y() - top.y()) * 0.42)
                    snow_cap.quadTo(0, top.y() + (left.y() - top.y()) * 0.35, top.x() + (right.x() - top.x()) * 0.45, top.y() + (right.y() - top.y()) * 0.42)
                    snow_cap.closeSubpath()
                    painter.setBrush(QColor(245, 250, 255, 215))
                    painter.drawPath(snow_cap)

            # Ornaments (archa qo'g'irchoqlari) with soft glow
            for i, (ox, oy, ocol) in enumerate(tr.ornaments):
                pulse = 0.65 + 0.35 * math.sin(self.time * 2.8 + tr.phase + i * 1.1)
                glow = QRadialGradient(ox, oy, 9.0)
                gc = QColor(ocol)
                gc.setAlpha(int(130 * pulse))
                glow.setColorAt(0.0, gc)
                glow.setColorAt(1.0, QColor(ocol.red(), ocol.green(), ocol.blue(), 0))
                painter.setBrush(QBrush(glow))
                painter.drawEllipse(QPointF(ox, oy), 9.0, 9.0)

                c = QColor(ocol)
                c.setAlpha(245)
                painter.setBrush(c)
                painter.drawEllipse(QPointF(ox, oy), 3.6, 3.6)
                painter.setBrush(QColor(255, 255, 255, 170))
                painter.drawEllipse(QPointF(ox - 1.1, oy - 1.1), 1.0, 1.0)

            # Golden star on top
            star_pulse = 0.75 + 0.25 * math.sin(self.time * 3.5 + tr.phase)
            sglow = QRadialGradient(0, -86, 13.0)
            sglow.setColorAt(0.0, QColor(255, 225, 90, int(170 * star_pulse)))
            sglow.setColorAt(1.0, QColor(255, 215, 60, 0))
            painter.setBrush(QBrush(sglow))
            painter.drawEllipse(QPointF(0, -86), 13.0, 13.0)

            star = QPainterPath()
            for j in range(10):
                ang = math.radians(j * 36 - 90)
                r = 6.5 if j % 2 == 0 else 2.8
                pt = QPointF(r * math.cos(ang), -86 + r * math.sin(ang))
                if j == 0:
                    star.moveTo(pt)
                else:
                    star.lineTo(pt)
            star.closeSubpath()
            painter.setBrush(QColor(255, 220, 70, 250))
            painter.drawPath(star)

            painter.restore()

    def _draw_snowmen(self, painter: QPainter) -> None:
        base_y = float(self.taskbar_y)
        for sm in self.snowmen:
            painter.save()
            painter.translate(sm.x, base_y)
            painter.scale(sm.scale, sm.scale)
            painter.rotate(math.degrees(sm.wobble))

            # Body (3 snowballs)
            painter.setPen(QPen(QColor(205, 222, 240, 220), 1.0))
            painter.setBrush(QColor(248, 252, 255, 245))
            painter.drawEllipse(QPointF(0, -11), 13, 12)
            painter.drawEllipse(QPointF(0, -27), 9.5, 9)
            painter.drawEllipse(QPointF(0, -40), 7.2, 7.2)

            # Buttons & Eyes
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(30, 35, 45, 240))
            painter.drawEllipse(QPointF(0, -29), 1.4, 1.4)
            painter.drawEllipse(QPointF(0, -24), 1.4, 1.4)
            painter.drawEllipse(QPointF(-2.4, -42), 1.2, 1.2)
            painter.drawEllipse(QPointF(2.4, -42), 1.2, 1.2)

            # Carrot nose
            nose = QPainterPath()
            nose.moveTo(0, -40)
            nose.lineTo(6.5, -39)
            nose.lineTo(0, -37.5)
            nose.closeSubpath()
            painter.setBrush(QColor(245, 130, 35, 245))
            painter.drawPath(nose)

            # Scarf
            painter.setBrush(sm.scarf_color)
            painter.drawRoundedRect(QRectF(-7.5, -34.5, 15, 3.6), 1.8, 1.8)
            flutter = math.sin(self.time * 3.5 + sm.x * 0.01) * 2.5
            tail = QPainterPath()
            tail.moveTo(3, -33)
            tail.lineTo(10 + flutter, -24)
            tail.lineTo(6 + flutter, -22)
            tail.lineTo(1, -31)
            tail.closeSubpath()
            painter.drawPath(tail)

            # Top hat
            painter.setBrush(sm.hat_color)
            painter.drawRoundedRect(QRectF(-8.5, -47.5, 17, 2.6), 1.2, 1.2)
            painter.drawRoundedRect(QRectF(-5.5, -56.5, 11, 9.5), 1.5, 1.5)

            painter.restore()

    def _draw_bulldozer(self, painter: QPainter) -> None:
        base_y = float(self.taskbar_y)

        # Exhaust puffs
        painter.setPen(Qt.NoPen)
        for pf in self.exhaust:
            painter.setBrush(QColor(215, 220, 230, int(255 * pf.alpha)))
            painter.drawEllipse(QPointF(pf.x, pf.y), pf.r, pf.r)

        for dz in self.dozers:
            bounce = abs(math.sin(dz.wheel_phase * 1.4)) * 1.3
            painter.save()
            painter.translate(dz.x, base_y - bounce)
            if dz.dir < 0:
                painter.scale(-1.0, 1.0)

            # Headlight beam
            beam = QPainterPath()
            beam.moveTo(23, -18)
            beam.lineTo(82, -28)
            beam.lineTo(82, -2)
            beam.closeSubpath()
            bgrad = QLinearGradient(23, -15, 82, -15)
            bgrad.setColorAt(0.0, QColor(255, 240, 150, 110))
            bgrad.setColorAt(1.0, QColor(255, 240, 150, 0))
            painter.setBrush(QBrush(bgrad))
            painter.drawPath(beam)

            # Exhaust pipe
            painter.setBrush(QColor(70, 75, 85, 245))
            painter.drawRoundedRect(QRectF(-6, -36, 4, 14), 1.5, 1.5)

            # Body & Engine hood (warm construction yellow)
            painter.setBrush(QColor(245, 185, 28, 252))
            painter.setPen(QPen(QColor(175, 120, 10, 220), 1.0))
            painter.drawRoundedRect(QRectF(-22, -24, 44, 14), 3, 3)

            # Cab
            painter.drawRoundedRect(QRectF(-20, -39, 22, 16), 3, 3)
            # Cab window
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(140, 205, 245, 225))
            painter.drawRoundedRect(QRectF(-16, -36, 14, 10), 2, 2)

            # Headlight bulb
            painter.setBrush(QColor(255, 248, 180, 255))
            painter.drawEllipse(QPointF(22, -18), 2.5, 2.5)

            # Tracks / Treads
            painter.setBrush(QColor(42, 46, 54, 250))
            painter.setPen(QPen(QColor(20, 22, 28, 255), 1.2))
            painter.drawRoundedRect(QRectF(-23, -11, 44, 11), 5.5, 5.5)
            # Wheels inside tracks
            painter.setBrush(QColor(135, 142, 155, 240))
            painter.setPen(Qt.NoPen)
            for wx in (-16, -5, 6, 15):
                painter.drawEllipse(QPointF(wx, -5.5), 3.3, 3.3)

            # Plow arm + curved front snowplow blade
            painter.setPen(QPen(QColor(85, 92, 105, 245), 3.0))
            painter.drawLine(QPointF(16, -9), QPointF(34, -8))

            blade = QPainterPath()
            blade.moveTo(32, -22)
            blade.quadTo(41, -11, 37, 0)
            blade.lineTo(32, 0)
            blade.quadTo(35, -11, 29, -20)
            blade.closeSubpath()
            painter.setPen(QPen(QColor(170, 110, 15, 230), 1.0))
            painter.setBrush(QColor(250, 195, 45, 252))
            painter.drawPath(blade)

            painter.restore()
