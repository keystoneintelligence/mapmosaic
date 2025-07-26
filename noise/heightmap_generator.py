import numpy as np
from PIL import Image
from opensimplex import OpenSimplex


class HeightmapGenerator:
    def __init__(
        self,
        seed: int = 42,
        base_freq: float = 0.005,
        octaves: int = 6,
        lacunarity: float = 2.2,
        gain: float = 0.5,
        warp_amp: float = 0.1,
        warp_freq: float = 0.02,
    ):
        """
        Args:
            seed: RNG seed
            base_freq: base frequency (larger→smaller features)
            octaves: number of fBm octaves
            lacunarity: frequency multiplier per octave
            gain: amplitude multiplier per octave
            warp_amp: strength of domain warp
            warp_freq: frequency of warp noise
        """
        self.noise = OpenSimplex(seed)
        self.base_freq = base_freq
        self.octaves = octaves
        self.lacunarity = lacunarity
        self.gain = gain
        self.warp_amp = warp_amp
        self.warp_freq = warp_freq

    def _fbm2d(self, x: float, y: float) -> float:
        total = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_amp = 0.0
        for _ in range(self.octaves):
            total   += self.noise.noise2(x * frequency, y * frequency) * amplitude
            max_amp += amplitude
            amplitude *= self.gain
            frequency *= self.lacunarity
        return total / max_amp

    def _domain_warp(self, x: float, y: float) -> (float, float):
        dx = self.noise.noise2(x * self.warp_freq, y * self.warp_freq)
        dy = self.noise.noise2((x + 1000) * self.warp_freq,
                                (y + 1000) * self.warp_freq)
        return x + dx * self.warp_amp, y + dy * self.warp_amp

    def generate(self, width: int, height: int) -> Image.Image:
        """
        Generate a greyscale heightmap of the given size.
        Returns a PIL.Image in mode 'L'.
        """
        arr = np.zeros((height, width), dtype=np.float32)
        for iy in range(height):
            for ix in range(width):
                wx, wy = ix * self.base_freq, iy * self.base_freq
                ux, uy = self._domain_warp(wx, wy)
                arr[iy, ix] = self._fbm2d(ux, uy)

        # Normalize to [0,1]
        arr = (arr - arr.min()) / (arr.max() - arr.min())
        # Convert to 8‑bit grayscale
        return Image.fromarray((arr * 255).astype('uint8'), mode='L')
