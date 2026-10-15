export async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch("/api" + path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : (detail?.[0]?.msg ??
            `Service unavailable (${response.status}). Please retry.`),
    );
  }
  return data as T;
}
