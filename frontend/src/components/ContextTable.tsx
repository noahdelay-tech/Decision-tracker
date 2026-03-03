import { cn } from "@/lib/utils";
import type { ContextRow } from "@/types/flag";

interface ContextTableProps {
  rows: ContextRow[];
  flaggedColumn: string;
}

export function ContextTable({ rows, flaggedColumn }: ContextTableProps) {
  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground italic">
        No row data available — context requires a file uploaded via the ingest endpoint.
      </p>
    );
  }

  // Derive ordered columns from the first row's keys
  const columns = Object.keys(rows[0].data);

  return (
    <div className="overflow-x-auto rounded-md border text-xs">
      <table className="min-w-full divide-y divide-border">
        <thead className="bg-muted/50">
          <tr>
            <th className="px-2 py-1.5 text-left font-medium text-muted-foreground w-12">#</th>
            {columns.map((col) => (
              <th
                key={col}
                className={cn(
                  "px-3 py-1.5 text-left font-medium whitespace-nowrap",
                  col === flaggedColumn ? "text-red-700 bg-red-50" : "text-muted-foreground"
                )}
              >
                {col}
                {col === flaggedColumn && (
                  <span className="ml-1 text-[10px] font-bold text-red-500">⚑</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border bg-background">
          {rows.map(({ row_index, data, is_flagged }) => (
            <tr
              key={row_index}
              className={cn(
                is_flagged && "bg-red-50/60 ring-1 ring-inset ring-red-200"
              )}
            >
              <td className="px-2 py-1.5 text-muted-foreground tabular-nums">
                {row_index}
              </td>
              {columns.map((col) => {
                const val = data[col];
                const isFlaggedCell = is_flagged && col === flaggedColumn;
                return (
                  <td
                    key={col}
                    className={cn(
                      "px-3 py-1.5 whitespace-nowrap tabular-nums",
                      isFlaggedCell
                        ? "font-bold text-red-700 bg-red-100/80"
                        : "text-foreground"
                    )}
                  >
                    {val === null || val === undefined ? (
                      <span className="text-muted-foreground/50">—</span>
                    ) : (
                      String(val)
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
