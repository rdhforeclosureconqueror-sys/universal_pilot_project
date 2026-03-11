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

    const response = await fetch(endpoint, {
      method,
      headers: {
        "Content-Type": "application/json",
      },
      body: method === "GET" || payload === undefined ? undefined : JSON.stringify(payload),
    });

    const data = await parseResponseBody(response);
    return {
      status: response.status,
      ok: response.ok,
      data,
    };
  },
};
