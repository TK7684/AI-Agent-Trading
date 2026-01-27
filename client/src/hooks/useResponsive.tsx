/**
 * Enhanced Responsive Hooks
 * Provides hooks for different breakpoints and device detection
 */

import * as React from "react";

// Breakpoint values (in px)
export const BREAKPOINTS = {
  xs: 375,   // Small mobile
  sm: 640,   // Mobile
  md: 768,   // Tablet
  lg: 1024,  // Laptop
  xl: 1280,  // Desktop
  '2xl': 1536, // Large desktop
} as const;

export type Breakpoint = keyof typeof BREAKPOINTS;

/**
 * Check if the viewport matches the given breakpoint
 */
function getMatches(breakpoint: Breakpoint): boolean {
  if (typeof window === 'undefined') return false;
  return window.innerWidth >= BREAKPOINTS[breakpoint];
}

/**
 * Hook to check if viewport is at or above the given breakpoint
 */
export function useBreakpoint(breakpoint: Breakpoint): boolean {
  const [matches, setMatches] = React.useState<boolean>(() => getMatches(breakpoint));

  React.useEffect(() => {
    const mql = window.matchMedia(`(min-width: ${BREAKPOINTS[breakpoint]}px)`);
    const onChange = () => setMatches(mql.matches);
    mql.addEventListener('change', onChange);
    setMatches(mql.matches);
    return () => mql.removeEventListener('change', onChange);
  }, [breakpoint]);

  return matches;
}

/**
 * Hook to get current breakpoint
 */
export function useCurrentBreakpoint(): Breakpoint {
  const [breakpoint, setBreakpoint] = React.useState<Breakpoint>('xs');

  React.useEffect(() => {
    const updateBreakpoint = () => {
      const width = window.innerWidth;
      if (width >= BREAKPOINTS['2xl']) setBreakpoint('2xl');
      else if (width >= BREAKPOINTS.xl) setBreakpoint('xl');
      else if (width >= BREAKPOINTS.lg) setBreakpoint('lg');
      else if (width >= BREAKPOINTS.md) setBreakpoint('md');
      else if (width >= BREAKPOINTS.sm) setBreakpoint('sm');
      else setBreakpoint('xs');
    };

    updateBreakpoint();
    window.addEventListener('resize', updateBreakpoint);
    return () => window.removeEventListener('resize', updateBreakpoint);
  }, []);

  return breakpoint;
}

/**
 * Hook to check if device is mobile (default breakpoint)
 */
export function useIsMobile() {
  return useBreakpoint('sm');
}

/**
 * Hook to check if device is tablet
 */
export function useIsTablet() {
  return useBreakpoint('md');
}

/**
 * Hook to check if device is desktop
 */
export function useIsDesktop() {
  return useBreakpoint('lg');
}

/**
 * Hook to get responsive value based on breakpoint
 */
export function useResponsiveValue<T>(values: Partial<Record<Breakpoint, T>>, defaultValue: T): T {
  const currentBreakpoint = useCurrentBreakpoint();

  // Find the largest breakpoint that matches and has a value
  const breakpointOrder: Breakpoint[] = ['2xl', 'xl', 'lg', 'md', 'sm', 'xs'];
  for (const bp of breakpointOrder) {
    if (BREAKPOINTS[bp] <= BREAKPOINTS[currentBreakpoint] && values[bp] !== undefined) {
      return values[bp]!;
    }
  }

  return defaultValue;
}

/**
 * Hook to detect touch device
 */
export function useIsTouchDevice(): boolean {
  const [isTouch, setIsTouch] = React.useState(false);

  React.useEffect(() => {
    const checkTouch = () => {
      setIsTouch(
        'ontouchstart' in window ||
        navigator.maxTouchPoints > 0 ||
        // @ts-ignore
        navigator.msMaxTouchPoints > 0
      );
    };

    checkTouch();
    return () => {}; // No cleanup needed
  }, []);

  return isTouch;
}

/**
 * Hook to get viewport dimensions
 */
export function useViewport() {
  const [viewport, setViewport] = React.useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 1024,
    height: typeof window !== 'undefined' ? window.innerHeight : 768,
  });

  React.useEffect(() => {
    const handleResize = () => {
      setViewport({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return viewport;
}

/**
 * Hook to detect orientation
 */
export function useOrientation() {
  const [orientation, setOrientation] = React.useState<'portrait' | 'landscape'>(
    typeof window !== 'undefined'
      ? window.innerHeight > window.innerWidth
        ? 'portrait'
        : 'landscape'
      : 'landscape'
  );

  React.useEffect(() => {
    const handleResize = () => {
      setOrientation(window.innerHeight > window.innerWidth ? 'portrait' : 'landscape');
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return orientation;
}
