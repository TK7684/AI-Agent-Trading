/**
 * Responsive Card Grid
 * Mobile-optimized card grid with adaptive columns
 */

import * as React from "react";
import { cn } from "@/lib/utils";
import { useBreakpoint } from "@/hooks/useResponsive";

export interface ResponsiveCardGridProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  /**
   * Minimum card width in pixels
   * @default 300
   */
  minCardWidth?: number;
  /**
   * Maximum columns (will be exceeded if cards are too small)
   * @default 4
   */
  maxColumns?: number;
  /**
   * Gap between cards in Tailwind spacing units
   * @default 4
   */
  gap?: number;
  /**
   * Use consistent card heights
   * @default true
   */
  uniformHeight?: boolean;
}

export function ResponsiveCardGrid({
  children,
  minCardWidth = 300,
  maxColumns = 4,
  gap = 4,
  uniformHeight = true,
  className,
  ...props
}: ResponsiveCardGridProps) {
  const isSm = useBreakpoint('sm');
  const isMd = useBreakpoint('md');
  const isLg = useBreakpoint('lg');
  const isXl = useBreakpoint('xl');

  // Calculate columns based on breakpoint
  const getColumns = () => {
    if (!isSm) return 1; // Mobile
    if (!isMd) return 2; // Tablet
    if (!isLg) return Math.min(3, maxColumns); // Small desktop
    if (!isXl) return Math.min(3, maxColumns); // Desktop
    return Math.min(4, maxColumns); // Large desktop
  };

  const columns = getColumns();
  const gapClass = `gap-${gap}`;

  return (
    <div
      className={cn(
        "grid",
        `grid-cols-1`,
        isSm && "sm:grid-cols-2",
        isLg && "lg:grid-cols-3",
        isXl && "xl:grid-cols-4",
        gapClass,
        uniformHeight && "grid-rows-[auto]",
        className
      )}
      style={{
        gridTemplateColumns: isSm
          ? isMd
            ? isLg
              ? isXl
                ? `repeat(${Math.min(4, maxColumns)}, minmax(0, 1fr))`
                : `repeat(${Math.min(3, maxColumns)}, minmax(0, 1fr))`
              : `repeat(2, minmax(0, 1fr))`
            : `repeat(2, minmax(0, 1fr))`
          : `repeat(1, minmax(0, 1fr))`,
      }}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * Responsive Card Container
 * Wraps content in a card that adapts to screen size
 */
export interface ResponsiveCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: "default" | "compact" | "detailed";
}

export function ResponsiveCard({
  children,
  variant = "default",
  className,
  ...props
}: ResponsiveCardProps) {
  const isMobile = !useBreakpoint('sm');

  return (
    <div
      className={cn(
        "rounded-lg border bg-card text-card-foreground",
        "transition-shadow hover:shadow-md",
        variant === "compact" && isMobile
          ? "p-3"
          : variant === "detailed"
          ? "p-6"
          : "p-4 sm:p-5",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * Mobile-optimized list item
 */
export interface MobileListItemProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  trailing?: React.ReactNode;
  onClick?: () => void;
}

export function MobileListItem({
  title,
  subtitle,
  icon,
  trailing,
  onClick,
  className,
  ...props
}: MobileListItemProps) {
  const isMobile = !useBreakpoint('sm');

  return (
    <div
      className={cn(
        "flex items-center gap-3 p-3 rounded-lg hover:bg-accent transition-colors cursor-pointer",
        "active:scale-[0.98] transition-transform",
        isMobile && "min-h-[60px]", // Touch-friendly minimum height
        className
      )}
      onClick={onClick}
      {...props}
    >
      {icon && (
        <div className="shrink-0">
          {icon}
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{title}</p>
        {subtitle && (
          <p className="text-xs text-muted-foreground truncate">{subtitle}</p>
        )}
      </div>
      {trailing && (
        <div className="shrink-0">
          {trailing}
        </div>
      )}
    </div>
  );
}

/**
 * Swipeable card container for mobile
 */
export interface SwipeableCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  swipeThreshold?: number;
}

export function SwipeableCard({
  children,
  onSwipeLeft,
  onSwipeRight,
  swipeThreshold = 50,
  className,
  ...props
}: SwipeableCardProps) {
  const [touchStart, setTouchStart] = React.useState<number | null>(null);
  const [touchEnd, setTouchEnd] = React.useState<number | null>(null);

  const minSwipeDistance = swipeThreshold;

  const onTouchStart = (e: React.TouchEvent) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const onTouchMove = (e: React.TouchEvent) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const onTouchEnd = () => {
    if (!touchStart || !touchEnd) return;

    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > minSwipeDistance;
    const isRightSwipe = distance < -minSwipeDistance;

    if (isLeftSwipe && onSwipeLeft) {
      onSwipeLeft();
    }
    if (isRightSwipe && onSwipeRight) {
      onSwipeRight();
    }
  };

  return (
    <div
      className={cn("touch-action-pan-y", className)}
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      {...props}
    >
      {children}
    </div>
  );
}
