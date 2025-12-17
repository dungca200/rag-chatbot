'use client';

import { useEffect, useState, useCallback } from 'react';

type GlowZone = 'default' | 'sidebar' | 'card' | 'input' | 'button';

const glowColors: Record<GlowZone, { primary: string; secondary: string }> = {
  default: {
    primary: 'rgba(6, 182, 212, 0.4)',    // Cyan
    secondary: 'rgba(139, 92, 246, 0.3)',  // Violet
  },
  sidebar: {
    primary: 'rgba(139, 92, 246, 0.4)',    // Violet
    secondary: 'rgba(168, 85, 247, 0.3)',  // Purple
  },
  card: {
    primary: 'rgba(251, 191, 36, 0.3)',    // Amber/Gold
    secondary: 'rgba(251, 146, 60, 0.25)', // Orange
  },
  input: {
    primary: 'rgba(34, 211, 238, 0.4)',    // Bright Cyan
    secondary: 'rgba(6, 182, 212, 0.3)',   // Cyan
  },
  button: {
    primary: 'rgba(16, 185, 129, 0.4)',    // Emerald
    secondary: 'rgba(52, 211, 153, 0.3)',  // Green
  },
};

export function CursorGlow() {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isVisible, setIsVisible] = useState(false);
  const [zone, setZone] = useState<GlowZone>('default');

  const detectZone = useCallback((element: Element | null): GlowZone => {
    if (!element) return 'default';

    // Check the element and its parents for zone indicators
    let current: Element | null = element;

    while (current) {
      const tagName = current.tagName.toLowerCase();
      const classList = current.classList;

      // Button detection
      if (tagName === 'button' || classList.contains('btn') || current.getAttribute('role') === 'button') {
        return 'button';
      }

      // Input detection
      if (tagName === 'input' || tagName === 'textarea' || classList.contains('input')) {
        return 'input';
      }

      // Card detection
      if (classList.contains('glass-card') || classList.contains('glass') || classList.contains('card')) {
        return 'card';
      }

      // Sidebar detection
      if (current.getAttribute('data-sidebar') === 'true' ||
          classList.contains('sidebar') ||
          current.closest('[data-sidebar="true"]')) {
        return 'sidebar';
      }

      current = current.parentElement;
    }

    return 'default';
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setPosition({ x: e.clientX, y: e.clientY });
      if (!isVisible) setIsVisible(true);

      // Detect zone from element under cursor
      const element = document.elementFromPoint(e.clientX, e.clientY);
      const newZone = detectZone(element);
      if (newZone !== zone) {
        setZone(newZone);
      }
    };

    const handleMouseLeave = () => {
      setIsVisible(false);
    };

    const handleMouseEnter = () => {
      setIsVisible(true);
    };

    window.addEventListener('mousemove', handleMouseMove);
    document.body.addEventListener('mouseleave', handleMouseLeave);
    document.body.addEventListener('mouseenter', handleMouseEnter);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      document.body.removeEventListener('mouseleave', handleMouseLeave);
      document.body.removeEventListener('mouseenter', handleMouseEnter);
    };
  }, [isVisible, zone, detectZone]);

  const colors = glowColors[zone];

  return (
    <>
      {/* Main glow - subtle ambient */}
      <div
        className="pointer-events-none fixed inset-0 z-30 transition-opacity duration-300"
        style={{ opacity: isVisible ? 0.7 : 0 }}
      >
        <div
          className="absolute rounded-full blur-2xl"
          style={{
            width: '150px',
            height: '150px',
            transform: `translate(${position.x - 75}px, ${position.y - 75}px)`,
            background: `radial-gradient(circle, ${colors.primary} 0%, transparent 70%)`,
            transition: 'background 0.5s ease',
          }}
        />
      </div>

      {/* Secondary glow - accent color */}
      <div
        className="pointer-events-none fixed inset-0 z-30 transition-opacity duration-300"
        style={{ opacity: isVisible ? 0.5 : 0 }}
      >
        <div
          className="absolute rounded-full blur-xl"
          style={{
            width: '80px',
            height: '80px',
            transform: `translate(${position.x - 40}px, ${position.y - 40}px)`,
            background: `radial-gradient(circle, ${colors.secondary} 0%, transparent 70%)`,
            transition: 'background 0.5s ease',
          }}
        />
      </div>
    </>
  );
}
