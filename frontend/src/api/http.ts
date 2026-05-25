/**
 * HTTP client utilities for API communication.
 * 
 * Provides a typed fetch wrapper with error handling and JSON serialization.
 * Automatically detects when the backend API is unavailable.
 */

export class ApiError extends Error {
  /** HTTP status code from the response */
  constructor(message: string, public status: number) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Make a typed fetch request to the API.
 * 
 * Handles JSON serialization, error parsing, and provides helpful error messages.
 * Empty responses (204 No Content) are handled correctly.
 * 
 * @template T The expected response type
 * @param path API endpoint path (e.g., "/api/cars")
 * @param options Fetch options (headers, method, body, etc.)
 * @returns Parsed response data of type T
 * @throws ApiError if the response is not ok
 */
export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers
    },
    ...options
  });

  if (!response.ok) {
    const missingApi = path.startsWith("/api") && response.status === 404;
    let message = missingApi
      ? "Backend API is not available. Start FastAPI on port 8000 before using the dashboard."
      : `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (!(missingApi && body.detail === "Not Found")) {
        message = body.detail ?? message;
      }
    } catch {
      // Keep the message selected from the HTTP status above.
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
