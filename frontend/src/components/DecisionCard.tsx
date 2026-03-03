import { Pencil, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Decision } from "@/types/decision";

const STATUS_VARIANTS: Record<string, "success" | "info" | "warning" | "muted" | "destructive"> = {
  decided: "success",
  in_review: "info",
  pending: "warning",
  cancelled: "muted",
};

const PRIORITY_VARIANTS: Record<string, "destructive" | "warning" | "info" | "muted"> = {
  critical: "destructive",
  high: "warning",
  medium: "info",
  low: "muted",
};

interface DecisionCardProps {
  decision: Decision;
  onEdit: (decision: Decision) => void;
  onDelete: (id: number) => void;
}

export function DecisionCard({ decision, onEdit, onDelete }: DecisionCardProps) {
  const createdDate = new Date(decision.created_at).toLocaleDateString();

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base leading-snug">{decision.title}</CardTitle>
          <div className="flex shrink-0 gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => onEdit(decision)}
              aria-label="Edit decision"
            >
              <Pencil className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-destructive hover:text-destructive"
              onClick={() => onDelete(decision.id)}
              aria-label="Delete decision"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5 mt-1">
          <Badge variant={STATUS_VARIANTS[decision.status] ?? "outline"}>
            {decision.status.replace("_", " ")}
          </Badge>
          <Badge variant={PRIORITY_VARIANTS[decision.priority] ?? "outline"}>
            {decision.priority}
          </Badge>
          {decision.category && (
            <Badge variant="outline">{decision.category}</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-1.5">
        {decision.description && (
          <p className="text-sm text-muted-foreground line-clamp-2">{decision.description}</p>
        )}
        {decision.outcome && (
          <p className="text-sm border-l-2 border-primary pl-2 text-muted-foreground line-clamp-2">
            {decision.outcome}
          </p>
        )}
        <p className="text-xs text-muted-foreground pt-1">Created {createdDate}</p>
      </CardContent>
    </Card>
  );
}
