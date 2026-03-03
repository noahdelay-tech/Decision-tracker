import type { Flag } from "@/types/flag";

interface FlagStatsProps {
  flags: Flag[];
}

const STAT_CONFIG = [
  { status: "pending",    label: "Pending",    bg: "bg-amber-50",  ring: "ring-amber-200",  text: "text-amber-700",  dot: "bg-amber-400"  },
  { status: "confirmed",  label: "Confirmed",  bg: "bg-green-50",  ring: "ring-green-200",  text: "text-green-700",  dot: "bg-green-500"  },
  { status: "rejected",   label: "Rejected",   bg: "bg-red-50",    ring: "ring-red-200",    text: "text-red-700",    dot: "bg-red-400"    },
  { status: "overridden", label: "Overridden", bg: "bg-blue-50",   ring: "ring-blue-200",   text: "text-blue-700",   dot: "bg-blue-400"   },
] as const;

export function FlagStats({ flags }: FlagStatsProps) {
  const counts = flags.reduce<Record<string, number>>((acc, f) => {
    acc[f.status] = (acc[f.status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {STAT_CONFIG.map(({ status, label, bg, ring, text, dot }) => (
        <div
          key={status}
          className={`flex items-center gap-3 rounded-lg px-4 py-3 ring-1 ${bg} ${ring}`}
        >
          <span className={`h-2.5 w-2.5 rounded-full shrink-0 ${dot}`} />
          <div>
            <p className={`text-2xl font-bold leading-none ${text}`}>
              {counts[status] ?? 0}
            </p>
            <p className={`text-xs mt-0.5 ${text} opacity-80`}>{label}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
