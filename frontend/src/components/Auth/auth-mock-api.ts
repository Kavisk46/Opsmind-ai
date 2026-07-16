import authUsersData from "@/lib/mock-data/auth-users.json";

import type { AuthCredentials, AuthUser } from "./types";

const AUTH_DELAY_MS = 600;

// Fixed on purpose — there's no real inbox/SMS to deliver a code to, so this
// is the documented demo code for the OTP verification page.
export const MOCK_OTP_CODE = "123456";

interface MockUser {
  id: string;
  name: string;
  email: string;
  password: string;
  avatarUrl: string | null;
  isEmailVerified: boolean;
  requiresOtp: boolean;
}

export interface MockLoginResult {
  outcome: "authenticated" | "otpRequired" | "emailVerificationRequired";
  user: AuthUser;
}

// Seed data plus whatever Signup/Reset Password add or change during this
// session — module-scoped so it's shared across every page, not per-component
// local state. Resets on a full reload, same as the rest of this mock backend.
let mockUsers: MockUser[] = (authUsersData as MockUser[]).map((user) => ({
  ...user,
}));

function simulateDelay(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, AUTH_DELAY_MS));
}

function findUserByEmail(email: string): MockUser | undefined {
  const normalized = email.trim().toLowerCase();
  return mockUsers.find((user) => user.email.toLowerCase() === normalized);
}

function toPublicUser(user: MockUser): AuthUser {
  return {
    id: user.id,
    name: user.name,
    email: user.email,
    avatarUrl: user.avatarUrl ?? undefined,
  };
}

export async function mockLogin({
  email,
  password,
}: AuthCredentials): Promise<MockLoginResult> {
  await simulateDelay();

  const user = findUserByEmail(email);
  if (!user || user.password !== password) {
    throw new Error("Incorrect email or password.");
  }

  if (user.requiresOtp) {
    return { outcome: "otpRequired", user: toPublicUser(user) };
  }

  if (!user.isEmailVerified) {
    return { outcome: "emailVerificationRequired", user: toPublicUser(user) };
  }

  return { outcome: "authenticated", user: toPublicUser(user) };
}

export interface SignupInput {
  name: string;
  email: string;
  password: string;
}

export async function mockSignup({
  name,
  email,
  password,
}: SignupInput): Promise<AuthUser> {
  await simulateDelay();

  if (findUserByEmail(email)) {
    throw new Error("An account with this email already exists.");
  }

  const user: MockUser = {
    id: crypto.randomUUID(),
    name,
    email,
    password,
    avatarUrl: null,
    isEmailVerified: false,
    requiresOtp: false,
  };
  mockUsers = [...mockUsers, user];

  return toPublicUser(user);
}

export async function mockForgotPassword(
  email: string
): Promise<{ resetToken: string }> {
  await simulateDelay();

  if (!findUserByEmail(email)) {
    throw new Error("We couldn't find an account with that email.");
  }

  // A real backend would email a single-use link; this is a stand-in token
  // the demo carries via the URL so the reset-password page has something to
  // validate against.
  return { resetToken: "demo-reset-token" };
}

export interface ResetPasswordInput {
  email: string;
  token: string;
  password: string;
}

export async function mockResetPassword({
  email,
  token,
  password,
}: ResetPasswordInput): Promise<void> {
  await simulateDelay();

  if (token !== "demo-reset-token") {
    throw new Error("This reset link is invalid or has expired.");
  }

  const user = findUserByEmail(email);
  if (!user) {
    throw new Error("We couldn't find an account with that email.");
  }

  user.password = password;
}

export async function mockVerifyOtp({
  email,
  code,
}: {
  email: string;
  code: string;
}): Promise<AuthUser> {
  await simulateDelay();

  const user = findUserByEmail(email);
  if (!user) {
    throw new Error("We couldn't find an account with that email.");
  }

  if (code !== MOCK_OTP_CODE) {
    throw new Error("Invalid verification code. Please try again.");
  }

  return toPublicUser(user);
}

export async function mockResendOtp(_email: string): Promise<void> {
  await simulateDelay();
}

export async function mockVerifyEmail(email: string): Promise<void> {
  await simulateDelay();

  const user = findUserByEmail(email);
  if (!user) {
    throw new Error("We couldn't find an account with that email.");
  }

  user.isEmailVerified = true;
}

export async function mockResendVerificationEmail(
  _email: string
): Promise<void> {
  await simulateDelay();
}
