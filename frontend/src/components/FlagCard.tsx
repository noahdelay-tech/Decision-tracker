import { ArrowRight, ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { Flag } from "@/types/flag";

// ── Visual config maps ────────────────────────────────────────────────────

const SEVERITY_STYLES = {
  high:   { card: "border-red-200 bg-red-50/30",    badge: "bg-red-100 text-red-800",    dot: "bg-red-500"   },
  medium: { card: "border-amber-200 bg-amber-50/30", badge: "bg-amber-100 text-amber-800", dot: "bg-amber-500" },
  low:    { card: "border-teal-200 bg-teal-50/20",   badge: "bg-teal-100 text-teal-800",   dot: "bg-teal-500"  },
} as const;

const STATUS_BADGE: Record<string, string> = {
  pending:    "bg-gray-100 text-gray-600",
  confirmed:  "bg-green-100 text-green-800",
  rejected:   "bg-red-100 text-red-800",
  overridden: "bg-blue-100 text-blue-800",
};

interface FlagCardProps {
  flag: Flag;
  onReview: (flag: Flag) => void;
}

export function FlagCard({ flag, onReview }: FlagCardProps) {
  const sev = SEVERITY_STYLES[flag.severity] ?? SEVERITY_STYLES.low;
  const isPending = flag.status === "pending";

  return (
    <Card
      className={cn(
        "transition-shadow hover:shadow-md cursor-pointer",
        sev.card,
        !isPending && "opacity-80"
      )}
      onClick={() => onReview(flag)}
    >
      <CardHeader className="pb-2 pt-4 px-4">
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-1 min-w-0">
            {/* Column name + raw value */}
            <p className="font-semibold text-sm truncate text-foreground">
              {flag.column_name}
              <span className="mx-1.5 text-muted-foreground font-normal">·</span>
              <span className="font-mono text-red-700">{flag.raw_value}</span>
              {flag.proposed_value && (
                <>
                  <ArrowRight className="inline h-3 w-3 mx-1.5 text-muted-foreground" />
                  <span className="font-mono text-green-700">{flag.proposed_value}</span>
                </>
              )}
            </p>
            {/* Row index + flag type */}
            <p className="text-xs text-muted-foreground">
              Row {flag.row_index} · {flag.flag_type.replace(/_/g, " ")}
            </p>
          </div>

          {/* Severity dot */}
          <span className={cn("mt-0.5 h-2.5 w-2.5 rounded-full shrink-0", sev.dot)} />
        </div>

        {/* Badges */}
        <div className="flex flex-wrap gap-1.5 mt-1">
          <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium", sev.badge)}>
            {flag.severity}
          </span>
          <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium", STATUS_BADGE[flag.status])}>
            {flag.status}
          </span>
        </div>
      </CardHeader>

      <CardContent className="px-4 pb-4 space-y-3">
        {/* Biological reasoning excerpt */}
        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
          {flag.biological_reasoning}
        </p>

        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs w-full justify-between"
          onClick={(e) => { e.stopPropagation(); onReview(flag); }}
        >
          {isPending ? "Review now" : "View details"}
          <ChevronRight className="h-3.5 w-3.5" />
        </Button>
      </CardContent>
    </Card>
  );
}
