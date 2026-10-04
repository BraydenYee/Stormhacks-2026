"use client";

import { useRef, useState } from "react";

type Props = {
  disabled?: boolean;
  onRecorded: (blob: Blob) => void;
};

/** Push-to-talk: hold the button (or Space) to record, release to send. */
export default function Recorder({ disabled, onRecorded }: Props) {
  const [recording, setRecording] = useState(false);
  const [denied, setDenied] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  async function start() {
    if (disabled || recording) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunks.current = [];
      rec.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks.current, { type: rec.mimeType || "audio/webm" });
        // Ignore accidental taps — too small to contain speech.
        if (blob.size > 2000) onRecorded(blob);
      };
      rec.start();
      recorder.current = rec;
      setRecording(true);
    } catch {
      setDenied(true);
    }
  }

  function stop() {
    if (recorder.current?.state === "recording") recorder.current.stop();
    setRecording(false);
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        onPointerDown={start}
        onPointerUp={stop}
        onPointerLeave={recording ? stop : undefined}
        disabled={disabled}
        aria-label="Hold to talk"
        className={`h-20 w-20 select-none rounded-full text-sm font-medium text-white shadow-lg transition ${
          recording ? "scale-110 bg-red-600" : "bg-blue-600 hover:bg-blue-500"
        } disabled:opacity-40`}
      >
        {recording ? "Listening…" : "Hold to talk"}
      </button>
      {denied && <p className="text-xs text-red-600">Microphone access was blocked. Allow it in your browser settings.</p>}
    </div>
  );
}
