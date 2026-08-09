import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

// The "status === 200 ? await response.json() : fallback" unwrap, written by
// hand at ~90 fetch call sites in two styles. Returns the parsed body on a
// 200, else the fallback (and never touches the body on a non-200).
export async function okJson<T = unknown>(
  response: { status: number; json: () => Promise<T> } | null | undefined,
  fallback: T | null = null,
): Promise<T | null> {
  return response && response.status === 200 ? await response.json() : fallback
}

// Seconds -> "M:SS" (used by the conversation-dynamics panel timeline and
// silence stats). Pure and unit-tested.
export function fmtClock(sec: number): string {
  const s = Math.max(0, Math.round(sec))
  const m = Math.floor(s / 60)
  return `${m}:${String(s % 60).padStart(2, "0")}`
}
