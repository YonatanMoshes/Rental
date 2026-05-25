/**
 * Date utility functions.
 * 
 * Handles date formatting and ISO string generation for API communication.
 */

/**
 * Get today's date as an ISO 8601 date string (YYYY-MM-DD).
 * 
 * Uses the browser's local timezone to ensure correct date is sent to the API.
 * @returns Today's date in ISO format
 */
export function todayIsoDate(): string {
  const now = new Date();
  const localDate = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return localDate.toISOString().slice(0, 10);
}
