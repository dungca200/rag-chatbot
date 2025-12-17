'use client';

import { useCallback, useState } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { useAuthStore } from '@/lib/stores/auth-store';
import { apiClient } from '@/lib/api/client';
import type { LoginRequest, RegisterRequest, User, AuthTokens } from '@/types';

export function useAuth() {
  const router = useRouter();
  const { login: storeLogin, logout: storeLogout, isAuthenticated, user } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);

  const login = useCallback(async (data: LoginRequest) => {
    setIsLoading(true);
    try {
      const response = await apiClient.login(data.username, data.password);
      const userData: User = {
        id: response.user.id,
        username: response.user.username,
        email: response.user.email,
        is_staff: response.user.is_staff,
      };
      storeLogin(userData, response.tokens);
      toast.success('Login successful');
      router.push('/chat');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Login failed';
      toast.error(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [storeLogin, router]);

  const register = useCallback(async (data: RegisterRequest) => {
    setIsLoading(true);
    try {
      await apiClient.register(data);
      toast.success('Registration successful. Please login.');
      router.push('/login');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Registration failed';
      toast.error(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  const logout = useCallback(() => {
    apiClient.logout();
    storeLogout();
    toast.success('Logged out');
    router.push('/login');
  }, [storeLogout, router]);

  return {
    login,
    register,
    logout,
    isLoading,
    isAuthenticated,
    user,
  };
}
