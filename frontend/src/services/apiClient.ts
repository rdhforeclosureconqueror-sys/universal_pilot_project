export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface ApiRequestOptions {
  method?: HttpMethod;
  payload?: unknown;
}

export interface ApiResponse {
  status: number;
  ok: boolean;
  data: unknown;
}

export const AUTH_TOKEN_KEY = "auth_token";

export const getAuthToken = (): string => {
  if (typeof window === "undefined") {
    return "";
  }
  return localStorage.getItem(AUTH_TOKEN_KEY) || "";
};

export const clearAuthToken = (): void => {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.removeItem(AUTH_TOKEN_KEY);
};

const parseResponseBody = async (response: Response): Promise<unknown> => {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
};

export const apiClient = {
  async request(endpoint: string, options: ApiRequestOptions = {}): Promise<ApiResponse> {
    const { method = "POST", payload } = options;
    const token = getAuthToken();

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(endpoint, {
      method,
      headers,
      body: method === "GET" || payload === undefined ? undefined : JSON.stringify(payload),
    });

    const data = await parseResponseBody(response);

    if (response.status === 401) {
      clearAuthToken();
      if (typeof window !== "undefined") {
        window.location.hash = "#/login";
      }
    }

    return {
      status: response.status,
      ok: response.ok,
      data,
    };
  },
};
