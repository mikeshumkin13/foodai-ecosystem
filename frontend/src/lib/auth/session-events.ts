export const AUTHENTICATION_REQUIRED_EVENT = "foodai:authentication-required";

export function notifyAuthenticationRequired(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(AUTHENTICATION_REQUIRED_EVENT));
  }
}
