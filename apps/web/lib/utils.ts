import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Gộp class: `clsx` cho điều kiện, `tailwind-merge` để class sau thắng class trước. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
