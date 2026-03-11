import { useState } from "react";

import { apiClient, HttpMethod } from "../services/apiClient";

interface AdminActionButtonProps {
  label: string;
  endpoint: string;
  method: HttpMethod;
  payload?: unknown;
  onResult?: (result: {
    label: string;
    endpoint: string;
    method: HttpMethod;
    response: unknown;
    status: number;
    ok: boolean;
    requestedAt: string;
  }) => void;
}

export const AdminActionButton = ({
  label,
  endpoint,
  method,
  payload,
  onResult,
}: AdminActionButtonProps) => {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    try {
      const result = await apiClient.request(endpoint, { method, payload });
      onResult?.({
        label,
        endpoint,
        method,
        response: result.data,
        status: result.status,
        ok: result.ok,
        requestedAt: new Date().toISOString(),
      });
    } catch (error) {
      onResult?.({
        label,
        endpoint,
        method,
        response: {
          error: error instanceof Error ? error.message : String(error),
        },
        status: 0,
        ok: false,
        requestedAt: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <button className="admin-action-button" onClick={handleClick} disabled={loading} type="button">
      {loading ? "Running..." : label}
    </button>
  );
};
