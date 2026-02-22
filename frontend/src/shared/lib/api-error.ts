export function getApiErrorMessage(error: unknown, fallback = "Request failed."): string {
  if (typeof error !== "object" || error === null) {
    return fallback;
  }

  const candidate = error as {
    response?: {
      data?: {
        error?: { message?: string };
        detail?: { message?: string } | string;
      };
    };
    message?: string;
  };

  const appErrorMessage = candidate.response?.data?.error?.message;
  if (typeof appErrorMessage === "string" && appErrorMessage.trim()) {
    return appErrorMessage;
  }

  const detail = candidate.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    const detailMessage = detail.message;
    if (typeof detailMessage === "string" && detailMessage.trim()) {
      return detailMessage;
    }
  }

  if (typeof candidate.message === "string" && candidate.message.trim()) {
    return candidate.message;
  }

  return fallback;
}
