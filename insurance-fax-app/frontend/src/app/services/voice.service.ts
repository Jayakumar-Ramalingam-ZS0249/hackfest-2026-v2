import { Injectable } from "@angular/core";

/**
 * Thin wrapper around the browser's native SpeechRecognition API for
 * voice INPUT (speech-to-text) -- no external service or API key
 * involved. Feature-detected: when unsupported, callers get a clear
 * `false` from `isRecognitionSupported()` and must fall back to typed
 * input; this service never throws for "unsupported browser", it just
 * reports it.
 *
 * Voice OUTPUT (text-to-speech) intentionally does NOT live here.
 * Browser SpeechSynthesis exposes no underlying audio stream, so it
 * cannot drive real amplitude-based avatar lip-sync -- see
 * AudioPlaybackService + the backend /api/ai/tts endpoint, which
 * produce actual playable audio the AI Manager's robot avatar can
 * analyse in real time.
 */

// Minimal ambient typing for the non-standardized SpeechRecognition API
// (no @types package ships one that covers both prefixed and unprefixed
// global names across browsers).
interface SpeechRecognitionResultLike {
  isFinal: boolean;
  0: { transcript: string };
}
interface SpeechRecognitionEventLike extends Event {
  results: ArrayLike<SpeechRecognitionResultLike>;
}
interface SpeechRecognitionLike extends EventTarget {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start(): void;
  stop(): void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: any) => void) | null;
  onend: (() => void) | null;
}

function getSpeechRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  const w = window as any;
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

@Injectable({ providedIn: "root" })
export class VoiceService {
  private recognition: SpeechRecognitionLike | null = null;

  isRecognitionSupported(): boolean {
    return getSpeechRecognitionCtor() !== null;
  }

  startListening(onResult: (transcript: string) => void, onEnd: () => void, onError?: (message: string) => void): void {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      onError?.("Speech recognition is not supported in this browser.");
      return;
    }

    this.recognition = new Ctor();
    this.recognition.lang = "en-US";
    this.recognition.interimResults = false;
    this.recognition.continuous = false;

    this.recognition.onresult = (event: SpeechRecognitionEventLike) => {
      const transcript = Array.from(event.results)
        .map((r) => r[0].transcript)
        .join(" ")
        .trim();
      if (transcript) onResult(transcript);
    };
    this.recognition.onerror = (event: any) => {
      onError?.(event?.error || "Speech recognition error.");
    };
    this.recognition.onend = () => onEnd();

    try {
      this.recognition.start();
    } catch {
      onError?.("Could not start the microphone.");
    }
  }

  stopListening(): void {
    this.recognition?.stop();
  }
}
