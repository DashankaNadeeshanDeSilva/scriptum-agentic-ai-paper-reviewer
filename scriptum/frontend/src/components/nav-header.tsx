"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Upload,
  Settings,
  Shield,
  Menu,
  BookOpenText,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { ThemeToggle } from "@/components/theme-toggle";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/privacy", label: "Privacy", icon: Shield },
];

function NavLinks({ onClick }: { onClick?: () => void }) {
  const pathname = usePathname();

  return (
    <>
      {navItems.map((item) => {
        const isActive =
          item.href === "/"
            ? pathname === "/"
            : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onClick}
            className={cn(
              "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </Link>
        );
      })}
    </>
  );
}

export function NavHeader() {
  return (
    <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center px-4 sm:px-6">
        {/* Logo */}
        <Link href="/" className="mr-6 flex items-center gap-2">
          <BookOpenText className="h-5 w-5 text-primary" />
          <span className="font-heading text-lg font-bold tracking-tight">
            SCRIPTUM
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-1 md:flex">
          <NavLinks />
        </nav>

        {/* Right side */}
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />

          {/* Mobile menu */}
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="md:hidden">
                <Menu className="h-4 w-4" />
                <span className="sr-only">Menu</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64">
              <div className="flex items-center gap-2 pb-4">
                <BookOpenText className="h-5 w-5 text-primary" />
                <span className="font-heading text-lg font-bold">
                  SCRIPTUM
                </span>
              </div>
              <Separator />
              <nav className="mt-4 flex flex-col gap-1">
                <NavLinks />
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
