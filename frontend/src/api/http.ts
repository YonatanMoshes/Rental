export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = "ApiError";
  }
}

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
