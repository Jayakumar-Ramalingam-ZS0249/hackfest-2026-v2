import { Injectable } from "@angular/core";

/**
 * Thin wrapper around the browser's native Web Speech API
 * (SpeechSynthesis for text-to-speech, SpeechRecognition for
 * speech-to-text). Deliberately uses only built-in browser APIs --
 * no external TTS/STT service or API key is involved, so nothing
 * voice-related needs a backend credential.
 *
 * Both capabilities are feature-detected. When unsupported, callers
 * get a clear `false` from the `isXSupported()` methods and must fall
 * back to normal text input/output -- this service never throws for
 * "unsupported browser", it just reports it.
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

  isSynthesisSupported(): boolean {
    return typeof window !== "undefined" && "speechSynthesis" in window;
  }

  isRecognitionSupported(): boolean {
    return getSpeechRecognitionCtor() !== null;
  }

  /** Speaks the given text verbatim -- never a canned/demo sentence, always exactly what's on screen. */
  speak(text: string, onEnd: () => void, onError?: () => void): void {
    if (!this.isSynthesisSupported() || !text.trim()) {
      onError?.();
      return;
    }
    window.speechSynthesis.cancel(); // never overlap with a previous utterance
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.onend = () => onEnd();
    utterance.onerror = () => {
      onError?.();
      onEnd();
    };
    window.speechSynthesis.speak(utterance);
  }

  stopSpeaking(): void {
    if (this.isSynthesisSupported()) {
      window.speechSynthesis.cancel();
    }
  }

  get isSpeaking(): boolean {
    return this.isSynthesisSupported() && window.speechSynthesis.speaking;
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
