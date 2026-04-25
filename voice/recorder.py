"""
Voice capture using sounddevice + scipy (works on M1 Mac without PyAudio).
WisprFlow integration point: replace `record_and_transcribe` with WisprFlow API call.
"""

from __future__ import annotations
import threading
import io
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import speech_recognition as sr

SAMPLE_RATE = 16000
MAX_SECONDS = 15
SILENCE_THRESHOLD = 0.01   # RMS below this = silence
SILENCE_DURATION = 1.5     # seconds of silence before auto-stop


class VoiceRecorder:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self._is_recording = False

    @property
    def is_recording(self):
        return self._is_recording

    def record_and_transcribe(self, on_result, on_error, on_start=None):
        """
        Record from mic until silence or max duration, then transcribe via Google.
        Calls on_result(transcript) on success, on_error(msg) on failure.
        """
        def _worker():
            self._is_recording = True
            if on_start:
                on_start()
            try:
                frames = []
                silent_frames = 0
                block_size = int(SAMPLE_RATE * 0.1)   # 100ms blocks
                silence_blocks = int(SILENCE_DURATION / 0.1)
                max_blocks = int(MAX_SECONDS / 0.1)
                total_blocks = 0

                with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                    dtype='int16', blocksize=block_size) as stream:
                    # Brief warm-up read to settle mic levels
                    stream.read(block_size)
                    while total_blocks < max_blocks:
                        data, _ = stream.read(block_size)
                        frames.append(data.copy())
                        total_blocks += 1
                        rms = np.sqrt(np.mean(data.astype(np.float32) ** 2))
                        if rms < SILENCE_THRESHOLD * 32768:
                            silent_frames += 1
                        else:
                            silent_frames = 0
                        # Stop after silence, but only if we've heard something
                        if silent_frames >= silence_blocks and total_blocks > silence_blocks:
                            break

                audio_data = np.concatenate(frames, axis=0)

                # Convert to WAV bytes in memory
                buf = io.BytesIO()
                wav.write(buf, SAMPLE_RATE, audio_data)
                buf.seek(0)

                # Feed into SpeechRecognition (no PyAudio needed here)
                with sr.AudioFile(buf) as source:
                    audio = self.recognizer.record(source)
                transcript = self.recognizer.recognize_google(audio)
                on_result(transcript)

            except sr.UnknownValueError:
                on_error("Couldn't understand audio. Please try again.")
            except sr.RequestError as e:
                on_error(f"Speech service error: {e}")
            except sd.PortAudioError:
                on_error("No microphone found. Use manual text input.")
            except Exception as e:
                on_error(f"Recording error: {e}")
            finally:
                self._is_recording = False

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
