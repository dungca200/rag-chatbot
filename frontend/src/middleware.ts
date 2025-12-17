import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that don't require authentication
const publicRoutes = ['/login', '/register'];

// Routes that require authentication
const protectedRoutes = ['/chat', '/profile', '/settings', '/documents', '/admin'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check for auth token in cookies (set by client-side)
  // Note: In production, you'd want to verify the token server-side
  const authStorage = request.cookies.get('auth-storage');
  let isAuthenticated = false;

  if (authStorage) {
    try {
      const parsed = JSON.parse(authStorage.value);
      isAuthenticated = !!parsed?.state?.tokens?.access;
    } catch {
      isAuthenticated = false;
    }
  }

  // Redirect authenticated users away from auth pages
  if (isAuthenticated && publicRoutes.includes(pathname)) {
    return NextResponse.redirect(new URL('/chat', request.url));
  }

  // Redirect unauthenticated users to login
  if (!isAuthenticated && protectedRoutes.some(route => pathname.startsWith(route))) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files (public folder)
     * - api routes (handled by backend)
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\..*|api).*)',
  ],
};
