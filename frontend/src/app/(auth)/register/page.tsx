'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '@/lib/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Sparkles, ArrowRight } from 'lucide-react';

const registerSchema = z.object({
  username: z.string()
    .min(3, 'Username must be at least 3 characters')
    .max(50, 'Username must be less than 50 characters'),
  email: z.string().email('Invalid email address'),
  password: z.string()
    .min(8, 'Password must be at least 8 characters'),
  password_confirm: z.string(),
}).refine((data) => data.password === data.password_confirm, {
  message: "Passwords don't match",
  path: ['password_confirm'],
});

type RegisterFormData = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const { register: registerUser, isLoading } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    setError(null);
    try {
      await registerUser(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    }
  };

  return (
    <div className="w-full max-w-md animate-fade-up">
      <div className="glass rounded-3xl p-8 relative overflow-hidden">
        {/* Decorative gradient */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-accent-secondary via-accent to-accent-secondary" />

        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex p-4 rounded-2xl glass mb-4 glow">
            <Sparkles className="h-8 w-8 text-accent" />
          </div>
          <h1 className="text-display text-3xl font-bold mb-2">
            <span className="text-gradient">Create account</span>
          </h1>
          <p className="text-muted-foreground">
            Get started with RAG Chat
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
            placeholder="Choose a username"
            error={errors.username?.message}
            {...register('username')}
          />

          <Input
            label="Email"
            type="email"
            placeholder="Enter your email"
            error={errors.email?.message}
            {...register('email')}
          />

          <Input
            label="Password"
            type="password"
            placeholder="Create a password"
            error={errors.password?.message}
            {...register('password')}
          />

          <Input
            label="Confirm Password"
            type="password"
            placeholder="Confirm your password"
            error={errors.password_confirm?.message}
            {...register('password_confirm')}
          />

          <Button
            type="submit"
            className="w-full group"
            size="lg"
            isLoading={isLoading}
          >
            Create account
            <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
          </Button>
        </form>

        <div className="mt-8 text-center">
          <p className="text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link
              href="/login"
              className="text-accent hover:text-accent-secondary transition-colors font-medium"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
