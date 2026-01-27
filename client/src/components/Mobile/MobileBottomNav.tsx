/**
 * Mobile Bottom Navigation
 * Bottom navigation bar for mobile devices with haptic feedback
 */

import * as React from "react";
import { useLocation } from "wouter";
import { Home, Compass, Star, Scale, Menu, Bell, User } from "lucide-react";
import { useIsMobile } from "@/hooks/useMobile";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { APP_LOGO, APP_TITLE } from "@/const";
import { useAuth } from "@/_core/hooks/useAuth";
import { cn } from "@/lib/utils";

interface NavItem {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  path: string;
  badge?: number;
}

const navItems: NavItem[] = [
  { icon: Home, label: "Home", path: "/dashboard" },
  { icon: Compass, label: "Discover", path: "/discover" },
  { icon: Star, label: "Watchlist", path: "/watchlist" },
  { icon: Scale, label: "Compare", path: "/comparison" },
];

interface MobileBottomNavProps {
  className?: string;
}

export function MobileBottomNav({ className }: MobileBottomNavProps) {
  const isMobile = useIsMobile();
  const [location] = useLocation();
  const { user } = useAuth();
  const [sheetOpen, setSheetOpen] = React.useState(false);

  if (!isMobile) return null;

  return (
    <>
      <nav
        className={cn(
          "fixed bottom-0 left-0 right-0 z-50 bg-background/95 backdrop-blur supports-[backdrop-filter]:backdrop-blur border-t",
          "pb-safe md:hidden",
          className
        )}
      >
        <div className="flex items-center justify-around h-16 px-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location === item.path;

            return (
              <button
                key={item.path}
                onClick={() => {
                  // Haptic feedback on supported devices
                  if ('vibrate' in navigator) {
                    navigator.vibrate(10);
                  }
                  window.location.href = item.path;
                }}
                className={cn(
                  "flex flex-col items-center justify-center gap-1 min-w-0 flex-1 py-1",
                  "relative transition-colors",
                  isActive
                    ? "text-primary"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <div className="relative">
                  <Icon className="h-5 w-5" />
                  {item.badge && item.badge > 0 && (
                    <Badge
                      variant="destructive"
                      className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
                    >
                      {item.badge > 9 ? '9+' : item.badge}
                    </Badge>
                  )}
                </div>
                <span className="text-[10px] font-medium truncate max-w-full">
                  {item.label}
                </span>
              </button>
            );
          })}

          {/* More menu button */}
          <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
            <SheetTrigger asChild>
              <button
                onClick={() => {
                  if ('vibrate' in navigator) {
                    navigator.vibrate(10);
                  }
                }}
                className="flex flex-col items-center justify-center gap-1 min-w-0 flex-1 py-1 text-muted-foreground hover:text-foreground"
              >
                <Menu className="h-5 w-5" />
                <span className="text-[10px] font-medium">More</span>
              </button>
            </SheetTrigger>
            <SheetContent side="bottom" className="h-auto rounded-t-xl">
              <MobileMenuContent onClose={() => setSheetOpen(false)} />
            </SheetContent>
          </Sheet>
        </div>
      </nav>

      {/* Add padding to bottom of page to account for fixed nav */}
      <div className="h-16 md:hidden" />
    </>
  );
}

function MobileMenuContent({ onClose }: { onClose: () => void }) {
  const { user, logout } = useAuth();

  const menuSections = [
    {
      title: "Features",
      items: [
        { icon: Bell, label: "Notifications", path: "/notifications" },
        { icon: Star, label: "My Subscriptions", path: "/subscription" },
        { icon: Scale, label: "Security Tools", path: "/security" },
      ],
    },
    {
      title: "Account",
      items: [
        { icon: User, label: "Profile Settings", path: "/settings" },
      ],
    },
  ];

  return (
    <div className="space-y-6 py-4">
      {/* User info */}
      <div className="flex items-center gap-3 px-4">
        <Avatar className="h-12 w-12 border">
          <AvatarFallback className="text-sm font-medium">
            {user?.name?.charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{user?.name || "User"}</p>
          <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
        </div>
      </div>

      {/* Menu sections */}
      {menuSections.map((section) => (
        <div key={section.title} className="space-y-2">
          <p className="px-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            {section.title}
          </p>
          {section.items.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.path}
                onClick={() => {
                  window.location.href = item.path;
                  onClose();
                }}
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-accent transition-colors text-left"
              >
                <Icon className="h-5 w-5 text-muted-foreground" />
                <span className="flex-1 text-sm">{item.label}</span>
              </button>
            );
          })}
        </div>
      ))}

      {/* Logout */}
      <button
        onClick={() => {
          logout();
          onClose();
        }}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-destructive/10 transition-colors text-left text-destructive"
      >
        <svg
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
          />
        </svg>
        <span className="flex-1 text-sm font-medium">Sign Out</span>
      </button>

      {/* App info */}
      <div className="flex items-center justify-center gap-2 px-4 pt-4 border-t">
        <img src={APP_LOGO} alt={APP_TITLE} className="h-6 w-6 rounded" />
        <span className="text-xs text-muted-foreground">{APP_TITLE}</span>
      </div>
    </div>
  );
}

export default MobileBottomNav;
