import { Link, useLocation, useMatch } from "react-router-dom";
import { ClipboardList, ScrollText, LayoutDashboard, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface NavProps {
  pendingCount?: number;
}

const TABS = [
  {
    to: "/",
    label: "Dashboard",
    icon: <LayoutDashboard className="h-4 w-4" />,
    match: (p: string) => p === "/" || p.startsWith("/studies"),
  },
  {
    to: "/queue",
    label: "Review Queue",
    icon: <ClipboardList className="h-4 w-4" />,
    match: (p: string) => p === "/queue" || p.startsWith("/review"),
  },
  {
    to: "/log",
    label: "Decision Log",
    icon: <ScrollText className="h-4 w-4" />,
    match: (p: string) => p === "/log",
  },
];

function StudyBreadcrumb() {
  const studyMatch = useMatch("/studies/:studyId");
  if (!studyMatch) return null;
  return (
    <div className="flex items-center gap-1 text-xs text-muted-foreground">
      <ChevronRight className="h-3 w-3" />
      <span className="text-slate-600">Study {studyMatch.params.studyId}</span>
    </div>
  );
}

export function Nav({ pendingCount }: NavProps) {
  const { pathname } = useLocation();
  const onStudyDetail = pathname.startsWith("/studies/");

  return (
    <header className="border-b bg-white" style={{ height: 56 }}>
      <div className="max-w-screen-2xl mx-auto px-4 h-full flex items-center gap-6">
        {/* Brand */}
        <span className="font-semibold text-sm tracking-tight text-slate-800 shrink-0">
          Data Review
        </span>

        {/* Tabs */}
        <nav className="flex gap-1">
          {TABS.map((tab) => {
            const active = tab.match(pathname);
            return (
              <Link
                key={tab.to}
                to={tab.to}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                  active
                    ? "bg-slate-100 text-slate-900"
                    : "text-slate-500 hover:text-slate-700 hover:bg-slate-50"
                )}
              >
                {tab.icon}
                {tab.label}
                {tab.to === "/queue" && pendingCount !== undefined && pendingCount > 0 && (
                  <span className="ml-0.5 inline-flex items-center justify-center rounded-full bg-amber-500 text-white text-[10px] font-bold min-w-[18px] h-[18px] px-1">
                    {pendingCount}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Breadcrumb — visible only on study detail pages */}
        {onStudyDetail && <StudyBreadcrumb />}
      </div>
    </header>
  );
}
