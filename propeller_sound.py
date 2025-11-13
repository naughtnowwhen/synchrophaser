"""
Real-time propeller sound synthesis.

Generates realistic propeller/drone sounds based on actual propeller RPM.
Key features:
- Blade Passage Frequency (BPF) = (RPM/60) * num_blades
- Harmonics for realistic timbre
- Sawtooth waveform (models sharp blade passages)
- Beating/phasing audible when propellers out of sync

Based on propeller acoustics research:
- BPF is dominant frequency
- Harmonics at 2x, 3x, 4x BPF
- Waveform has sharp attacks (blade passages)

Author: Based on acoustic research
Date: 2025-11-12
"""

import numpy as np
import threading
import time


class PropellerSoundGenerator:
    """
    Real-time propeller sound synthesis.

    Generates audio based on two propeller RPMs, creating realistic
    drone/propeller sounds with proper blade passage frequencies.

    When propellers are out of sync, you'll hear beating (wah-wah effect)
    due to frequency difference.
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        num_blades: int = 3,
        volume: float = 0.15,
    ):
        """
        Initialize sound generator.

        Args:
            sample_rate: Audio sample rate (Hz)
            num_blades: Number of blades per propeller (3 or 4 typical)
            volume: Master volume (0.0 to 1.0, default 0.15 = gentle)
        """
        self.sample_rate = sample_rate
        self.num_blades = num_blades
        self.volume = volume

        # Current propeller RPMs (will be updated from simulation)
        self.rpm_main = 2400.0
        self.rpm_follower = 2400.0

        # Audio state
        self.enabled = False
        self.stream = None
        self.phase_main = 0.0
        self.phase_follower = 0.0

        # Harmonic structure (amplitude of each harmonic)
        # Fundamental=1.0, 2nd=0.5, 3rd=0.25, 4th=0.125
        self.harmonic_amplitudes = [1.0, 0.5, 0.25, 0.125]

        # Try to import sounddevice
        try:
            import sounddevice as sd
            self.sd = sd
            self.available = True
        except ImportError:
            self.sd = None
            self.available = False
            print("Warning: sounddevice not available. Install with: pip install sounddevice")

    def rpm_to_bpf(self, rpm: float) -> float:
        """
        Convert RPM to Blade Passage Frequency (BPF).

        BPF = (RPM / 60) * num_blades

        This is the fundamental frequency you hear from the propeller.

        Args:
            rpm: Propeller RPM

        Returns:
            BPF in Hz
        """
        return (rpm / 60.0) * self.num_blades

    def generate_propeller_tone(
        self,
        bpf: float,
        phase: float,
        num_samples: int,
    ) -> tuple[np.ndarray, float]:
        """
        Generate one propeller's sound using additive synthesis.

        Uses sawtooth-like waveform with harmonics to model blade passages.

        Args:
            bpf: Blade passage frequency (Hz)
            phase: Current phase (radians)
            num_samples: Number of samples to generate

        Returns:
            Tuple of (audio samples, new phase)
        """
        # Time array for this block
        t = np.arange(num_samples) / self.sample_rate

        # Generate signal with harmonics
        signal = np.zeros(num_samples)

        for harmonic_num, amplitude in enumerate(self.harmonic_amplitudes, start=1):
            freq = bpf * harmonic_num
            # Use sine waves for each harmonic (additive synthesis)
            harmonic = amplitude * np.sin(2.0 * np.pi * freq * t + phase)
            signal += harmonic

        # Normalize
        signal = signal / len(self.harmonic_amplitudes)

        # Update phase for continuity
        new_phase = (phase + 2.0 * np.pi * bpf * num_samples / self.sample_rate) % (2.0 * np.pi)

        return signal, new_phase

    def audio_callback(self, outdata, frames, time_info, status):
        """
        Audio callback function (called by sounddevice).

        Generates audio in real-time based on current propeller RPMs.

        Args:
            outdata: Output buffer to fill
            frames: Number of frames to generate
            time_info: Timing information (unused)
            status: Status flags (unused)
        """
        if status:
            print(f"Audio status: {status}")

        # Get current BPFs from RPMs
        bpf_main = self.rpm_to_bpf(self.rpm_main)
        bpf_follower = self.rpm_to_bpf(self.rpm_follower)

        # Generate sound for each propeller
        signal_main, self.phase_main = self.generate_propeller_tone(
            bpf_main, self.phase_main, frames
        )
        signal_follower, self.phase_follower = self.generate_propeller_tone(
            bpf_follower, self.phase_follower, frames
        )

        # Mix both propellers (simple average)
        # When they're in sync, this adds constructively
        # When out of sync, you hear beating
        mixed = (signal_main + signal_follower) / 2.0

        # Apply master volume
        mixed = mixed * self.volume

        # Soft clipping to prevent distortion
        mixed = np.tanh(mixed)

        # Write to output buffer (mono for now, duplicate to stereo)
        outdata[:, 0] = mixed
        if outdata.shape[1] > 1:
            outdata[:, 1] = mixed

    def start(self):
        """Start audio generation."""
        if not self.available:
            print("Sound not available (sounddevice not installed)")
            return False

        if self.enabled:
            return True  # Already running

        try:
            # Start audio stream
            self.stream = self.sd.OutputStream(
                samplerate=self.sample_rate,
                channels=2,  # Stereo
                callback=self.audio_callback,
                blocksize=2048,  # Larger blocks for stability
            )
            self.stream.start()
            self.enabled = True
            print("✓ Propeller sound started")
            return True

        except Exception as e:
            print(f"Failed to start audio: {e}")
            return False

    def stop(self):
        """Stop audio generation."""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.enabled = False
        print("✓ Propeller sound stopped")

    def update_rpms(self, rpm_main: float, rpm_follower: float):
        """
        Update propeller RPMs (called from simulation).

        This changes the frequencies in real-time.

        Args:
            rpm_main: Main propeller RPM
            rpm_follower: Follower propeller RPM
        """
        self.rpm_main = rpm_main
        self.rpm_follower = rpm_follower

    def set_volume(self, volume: float):
        """
        Set master volume.

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.volume = np.clip(volume, 0.0, 1.0)

    def is_available(self) -> bool:
        """Check if sound is available."""
        return self.available

    def __del__(self):
        """Cleanup on deletion."""
        self.stop()


def test_sound():
    """Test propeller sound generation."""
    print("="*60)
    print("PROPELLER SOUND TEST")
    print("="*60)

    # Create sound generator
    sound = PropellerSoundGenerator(num_blades=3, volume=0.2)

    if not sound.is_available():
        print("❌ Sound not available (install sounddevice)")
        return

    print(f"\nConfiguration:")
    print(f"  Sample rate: {sound.sample_rate} Hz")
    print(f"  Num blades: {sound.num_blades}")
    print(f"  Volume: {sound.volume}")

    print(f"\nBlade Passage Frequencies:")
    print(f"  At 2400 RPM: {sound.rpm_to_bpf(2400.0):.1f} Hz")
    print(f"  At 2380 RPM: {sound.rpm_to_bpf(2380.0):.1f} Hz")
    print(f"  At 2420 RPM: {sound.rpm_to_bpf(2420.0):.1f} Hz")

    # Test 1: Both propellers at same RPM
    print("\n" + "="*60)
    print("TEST 1: Both at 2400 RPM (in sync)")
    print("="*60)
    print("You should hear: Smooth, steady drone tone")
    print("Playing for 3 seconds...")

    sound.update_rpms(2400.0, 2400.0)
    sound.start()
    time.sleep(3)

    # Test 2: Slight RPM difference (beating)
    print("\n" + "="*60)
    print("TEST 2: Main=2400, Follower=2405 RPM (5 RPM difference)")
    print("="*60)
    bpf_diff = sound.rpm_to_bpf(2405.0) - sound.rpm_to_bpf(2400.0)
    print(f"BPF difference: {bpf_diff:.2f} Hz")
    print("You should hear: WOW-WOW-WOW beating effect")
    print("Playing for 5 seconds...")

    sound.update_rpms(2400.0, 2405.0)
    time.sleep(5)

    # Test 3: Larger RPM difference
    print("\n" + "="*60)
    print("TEST 3: Main=2400, Follower=2420 RPM (20 RPM difference)")
    print("="*60)
    bpf_diff = sound.rpm_to_bpf(2420.0) - sound.rpm_to_bpf(2400.0)
    print(f"BPF difference: {bpf_diff:.2f} Hz")
    print("You should hear: Faster beating/warbling")
    print("Playing for 5 seconds...")

    sound.update_rpms(2400.0, 2420.0)
    time.sleep(5)

    # Test 4: Back to sync
    print("\n" + "="*60)
    print("TEST 4: Both back to 2400 RPM (synced)")
    print("="*60)
    print("You should hear: Smooth tone again (beating stops)")
    print("Playing for 3 seconds...")

    sound.update_rpms(2400.0, 2400.0)
    time.sleep(3)

    sound.stop()

    print("\n" + "="*60)
    print("✓ Sound test complete")
    print("="*60)
    print("\nKey observations:")
    print("  - When RPMs match: smooth, steady tone")
    print("  - When RPMs differ: beating/phasing effect")
    print("  - Larger difference: faster beating")
    print("\nThis is EXACTLY what synchrophaser prevents!")


if __name__ == '__main__':
    test_sound()
