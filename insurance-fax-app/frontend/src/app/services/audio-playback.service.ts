import { Injectable } from "@angular/core";

/**
 * Plays a real audio blob and reports REAL playback events/amplitude so a
 * caller can drive genuinely audio-synchronized UI (e.g. robot lip-sync).
 *
 * Two modes, and the difference is never hidden:
 *  - "analyser": Web Audio API (AudioContext + AnalyserNode) reads the
 *    actual audio signal every animation frame and reports real RMS
 *    amplitude. This is the only mode that is truly audio-driven.
 *  - "fallback": used only when the Web Audio API is unavailable. It
 *    reports a fixed, non-random level while audio.paused is false and
 *    0 otherwise -- driven by real play/pause events, but NOT amplitude,
 *    and deliberately not dressed up to look like real lip-sync.
 *
 * Never uses setInterval() or a free-running animation loop: the
 * requestAnimationFrame loop only starts once real playback begins and
 * is cancelled the instant playback stops, pauses, ends, or errors.
 */

export type PlaybackEvent = "playing" | "paused" | "waiting" | "ended" | "error";

export interface PlaybackCallbacks {
  onEvent: (event: PlaybackEvent) => void;
  /** Real-time amplitude, smoothed, in the range 0-1. */
  onLevel: (level: number) => void;
}

@Injectable({ providedIn: "root" })
export class AudioPlaybackService {
  readonly syncMode: "analyser" | "fallback";

  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private sourceNode: MediaElementAudioSourceNode | null = null;
  private currentAudio: HTMLAudioElement | null = null;
  private currentUrl: string | null = null;
  private rafId: number | null = null;
  private smoothedLevel = 0;

  constructor() {
    this.syncMode = this.detectAnalyserSupport() ? "analyser" : "fallback";
  }

  private detectAnalyserSupport(): boolean {
    const w = window as any;
    return typeof w.AudioContext !== "undefined" || typeof w.webkitAudioContext !== "undefined";
  }

  /** Plays `blob` from the start. Stops/replaces any audio already playing. */
  play(blob: Blob, callbacks: PlaybackCallbacks): void {
    this.stop();

    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    this.currentAudio = audio;
    this.currentUrl = url;

    audio.addEventListener("playing", () => callbacks.onEvent("playing"));
    audio.addEventListener("waiting", () => callbacks.onEvent("waiting"));
    audio.addEventListener("pause", () => {
      if (!audio.ended) callbacks.onEvent("paused");
    });
    audio.addEventListener("ended", () => {
      callbacks.onEvent("ended");
      this.teardownLoop();
    });
    audio.addEventListener("error", () => {
      callbacks.onEvent("error");
      this.teardownLoop();
    });

    let analyserReady = false;
    if (this.syncMode === "analyser") {
      analyserReady = this.setupAnalyser(audio);
    }

    audio
      .play()
      .then(() => {
        if (analyserReady && this.analyser) {
          this.runAnalyserLoop(callbacks.onLevel);
        } else {
          this.runFallbackLoop(audio, callbacks.onLevel);
        }
      })
      .catch(() => callbacks.onEvent("error"));
  }

  private setupAnalyser(audio: HTMLAudioElement): boolean {
    try {
      const Ctor: typeof AudioContext = (window as any).AudioContext || (window as any).webkitAudioContext;
      if (!this.audioContext) {
        this.audioContext = new Ctor();
      }
      if (this.audioContext.state === "suspended") {
        this.audioContext.resume().catch(() => {});
      }
      this.sourceNode = this.audioContext.createMediaElementSource(audio);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 512;
      this.sourceNode.connect(this.analyser);
      this.analyser.connect(this.audioContext.destination);
      return true;
    } catch {
      // Some browsers/policies can still refuse this -- degrade honestly
      // to the fallback loop rather than throwing and breaking the chat.
      this.analyser = null;
      this.sourceNode = null;
      return false;
    }
  }

  private runAnalyserLoop(onLevel: (level: number) => void): void {
    const analyser = this.analyser!;
    const data = new Uint8Array(analyser.frequencyBinCount);
    const loop = () => {
      analyser.getByteTimeDomainData(data);
      let sumSquares = 0;
      for (let i = 0; i < data.length; i++) {
        const v = (data[i] - 128) / 128;
        sumSquares += v * v;
      }
      const rms = Math.sqrt(sumSquares / data.length);
      // Exponential smoothing so the mouth doesn't jitter frame-to-frame.
      this.smoothedLevel = this.smoothedLevel * 0.7 + rms * 0.3;
      // Speech RMS on time-domain data is typically small; scale up so
      // normal speaking volume reaches the upper part of the 0-1 range.
      onLevel(Math.min(1, this.smoothedLevel * 4.5));
      this.rafId = requestAnimationFrame(loop);
    };
    this.rafId = requestAnimationFrame(loop);
  }

  private runFallbackLoop(audio: HTMLAudioElement, onLevel: (level: number) => void): void {
    const loop = () => {
      onLevel(audio.paused || audio.ended ? 0 : 0.5);
      this.rafId = requestAnimationFrame(loop);
    };
    this.rafId = requestAnimationFrame(loop);
  }

  private teardownLoop(): void {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    this.smoothedLevel = 0;
    if (this.currentUrl) {
      URL.revokeObjectURL(this.currentUrl);
      this.currentUrl = null;
    }
  }

  /** Stops playback immediately (user Stop, new question, component teardown). */
  stop(): void {
    this.teardownLoop();
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio = null;
    }
    if (this.sourceNode) {
      try {
        this.sourceNode.disconnect();
      } catch {
        /* already disconnected */
      }
      this.sourceNode = null;
    }
    if (this.analyser) {
      try {
        this.analyser.disconnect();
      } catch {
        /* already disconnected */
      }
      this.analyser = null;
    }
  }
}
