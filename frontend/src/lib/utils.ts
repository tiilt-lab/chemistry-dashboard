import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

// Seconds -> "M:SS" (used by the conversation-dynamics panel timeline and
// silence stats). Pure and unit-tested.
export function fmtClock(sec: number): string {
  const s = Math.max(0, Math.round(sec))
  const m = Math.floor(s / 60)
  return `${m}:${String(s % 60).padStart(2, "0")}`
}

// Default pod group name when a joiner doesn't type one. Random suffix so two
// groups in one session don't collide onto the same device name.
export function defaultGroupName(rand: () => number = Math.random): string {
  return "Group " + Math.floor(100 + rand() * 900)
}
