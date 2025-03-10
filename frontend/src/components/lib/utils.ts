import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Combines multiple class values into a single className string,
 * with proper handling of Tailwind CSS classes.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function makeAPIURL(path: string): string {
  return `${process.env.NEXT_PUBLIC_API_URL || ''}/${path}`;
}
