'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '@/lib/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Zap, ArrowRight } from 'lucide-react';

const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { login, isLoading } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    setError(null);
    try {
      await login(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    }
  };

  return (
    <div className="w-full max-w-md animate-fade-up">
      <div className="glass rounded-3xl p-8 relative overflow-hidden">
        {/* Decorative gradient */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-accent via-accent-secondary to-accent" />

        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex p-4 rounded-2xl glass mb-4 glow">
            <Zap className="h-8 w-8 text-accent" />
          </div>
          <h1 className="text-display text-3xl font-bold mb-2">
            <span className="text-gradient">Welcome back</span>
          </h1>
          <p className="text-muted-foreground">
            Sign in to continue to RAG Chat
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          {error && (
            <div className="p-4 rounded-xl bg-error/10 border border-error/20 text-error text-sm animate-fade-up">
              {error}
            </div>
          )}

          <Input
            label="Username"
            placeholder="Enter your username"
            error={errors.username?.message}
            {...register('username')}
          />

          <Input
            label="Password"
            type="password"
            placeholder="Enter your password"
            error={errors.password?.message}
            {...register('password')}
          />

          <Button
            type="submit"
            className="w-full group"
            size="lg"
            isLoading={isLoading}
          >
            Sign in
            <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
          </Button>
        </form>

        <div className="mt-8 text-center">
          <p className="text-sm text-muted-foreground">
            Don&apos;t have an account?{' '}
            <Link
              href="/register"
              className="text-accent hover:text-accent-secondary transition-colors font-medium"
            >
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
