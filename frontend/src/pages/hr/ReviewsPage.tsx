import { useMemo, useState } from "react";
import {
  Search,
  Star,
  MessageSquareQuote,
  Filter,
  Sparkles,
  ShieldCheck,
  TriangleAlert,
  BarChart3,
} from "lucide-react";
import { useFeedbackList, useFeedbackStats } from "@/hooks/useQueries";
import { TableRowsSkeleton } from "@/components/shared/Skeleton";
import { SeverityBadge, StatusBadge } from "@/components/shared/Badges";
import { cn, formatDate } from "@/lib/utils";

function Stars({
  rating,
  size = 15,
}: {
  rating: number;
  size?: number;
}) {
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((value) => (
        <Star
          key={value}
          size={size}
          style={{
            fill: value <= Math.round(rating) ? "currentColor" : "none",
          }}
          className={cn(
            value <= Math.round(rating)
              ? "text-amber-400"
              : "text-slate-300",
          )}
        />
      ))}
      <span className="ml-1 text-xs font-semibold text-slate-600">
        {rating.toFixed(1)}
      </span>
    </div>
  );
}

function StatCard({
  title,
  value,
  hint,
  icon,
  tone,
}: {
  title: string;
  value: string | number;
  hint: string;
  icon: React.ReactNode;
  tone: string;
}) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[26px] border p-5 shadow-sm",
        tone,
      )}
    >
      <div className="absolute -right-5 -top-5 h-24 w-24 rounded-full bg-white/35 blur-2xl" />
      <div className="relative flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-700">{title}</p>
          <p className="mt-4 text-4xl font-bold tracking-tight text-slate-950">
            {value}
          </p>
          <p className="mt-2 text-sm text-slate-600">{hint}</p>
        </div>
        <div className="rounded-2xl border border-white/70 bg-white/75 p-3 text-slate-700 shadow-sm">
          {icon}
        </div>
      </div>
    </div>
  );
}

export default function ReviewsPage() {
  const [search, setSearch] = useState("");
  const [ratingFilter, setRatingFilter] = useState("");

  const { data: reviews = [], isLoading: reviewsLoading } = useFeedbackList();
  const { data: stats, isLoading: statsLoading } = useFeedbackStats();

  const filteredReviews = useMemo(() => {
    return reviews.filter((review) => {
      const matchesRating =
        !ratingFilter || String(Math.floor(review.rating)) === ratingFilter;
      const q = search.trim().toLowerCase();
      const matchesSearch =
        !q ||
        review.ticket_id.toLowerCase().includes(q) ||
        review.user_id.toLowerCase().includes(q) ||
        review.ticket_title.toLowerCase().includes(q) ||
        review.comment.toLowerCase().includes(q);
      return matchesRating && matchesSearch;
    });
  }, [ratingFilter, reviews, search]);

  const badReviews = reviews.filter((review) => review.rating <= 2).length;
  const withComments = reviews.filter((review) => review.comment.trim()).length;
  const averageRating = Number((stats?.average_rating ?? 0).toFixed(2));
  const averageTone =
    averageRating >= 4 ? "Strong sentiment" : averageRating >= 3 ? "Mixed sentiment" : "Needs attention";

  const ratingBars = [5, 4, 3, 2, 1].map((rating) => {
    const count = stats?.rating_distribution?.[String(rating)] ?? 0;
    const total = stats?.total ?? 0;
    const percent = total > 0 ? (count / total) * 100 : 0;
    return { rating, count, percent };
  });

  return (
    <div className="space-y-6">
      <section className="relative overflow-hidden rounded-[30px] border border-slate-200 bg-[radial-gradient(circle_at_top_left,_rgba(251,191,36,0.18),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(59,130,246,0.18),_transparent_30%),linear-gradient(135deg,_#ffffff,_#f8fafc_55%,_#eef4ff)] p-6 shadow-sm">
        <div className="absolute inset-y-0 right-0 hidden w-1/3 bg-[linear-gradient(180deg,rgba(15,23,42,0.02),rgba(15,23,42,0))] md:block" />
        <div className="relative grid gap-6 lg:grid-cols-[1.35fr_0.95fr]">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-white/85 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-amber-700 shadow-sm">
              <Sparkles size={13} />
              Feedback Intelligence
            </div>
            <h1 className="mt-4 text-3xl font-bold tracking-tight text-slate-950">
              Reviews
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
              A focused view of employee feedback on resolved tickets. Senior
              Authority can review the full picture, while HR only sees reviews
              allowed by the notification levels assigned to their account.
            </p>

            <div className="mt-5 flex flex-wrap gap-3">
              <div className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white/85 px-4 py-2 text-sm text-slate-700 shadow-sm">
                <ShieldCheck size={16} className="text-emerald-600" />
                Access follows assigned review severity coverage
              </div>
              <div className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white/85 px-4 py-2 text-sm text-slate-700 shadow-sm">
                <MessageSquareQuote size={16} className="text-blue-600" />
                {reviewsLoading ? "Loading comment insights…" : `${withComments} written comments captured`}
              </div>
            </div>
          </div>

          <div className="rounded-[26px] border border-slate-200/90 bg-white/80 p-5 shadow-sm backdrop-blur">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-500">
                  Snapshot
                </p>
                <div className="mt-3 flex items-end gap-3">
                  <span className="text-5xl font-bold tracking-tight text-slate-950">
                    {statsLoading ? "..." : averageRating.toFixed(2)}
                  </span>
                  <span className="pb-1 text-sm text-slate-500">/ 5.00</span>
                </div>
              </div>
              <div className="rounded-2xl bg-amber-100 p-3 text-amber-700">
                <BarChart3 size={22} />
              </div>
            </div>

            <div className="mt-3">
              <Stars rating={averageRating} size={17} />
              <p className="mt-2 text-sm font-medium text-slate-700">
                {averageTone}
              </p>
            </div>

            <div className="mt-5 space-y-3">
              {ratingBars.map((item) => (
                <div
                  key={item.rating}
                  className="grid grid-cols-[42px_1fr_32px] items-center gap-3"
                >
                  <div className="text-sm font-semibold text-slate-600">
                    {item.rating}★
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-amber-300 via-orange-400 to-rose-400"
                      style={{ width: `${item.percent}%` }}
                    />
                  </div>
                  <div className="text-right text-xs font-medium text-slate-500">
                    {item.count}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          title="Average Rating"
          value={statsLoading ? "..." : averageRating.toFixed(2)}
          hint="Overall satisfaction across visible reviews"
          icon={<Star size={20} />}
          tone="border-amber-200 bg-gradient-to-br from-amber-50 via-white to-orange-50"
        />
        <StatCard
          title="Visible Reviews"
          value={statsLoading ? "..." : stats?.total ?? 0}
          hint="Reviews currently visible to this role"
          icon={<ShieldCheck size={20} />}
          tone="border-blue-200 bg-gradient-to-br from-blue-50 via-white to-cyan-50"
        />
        <StatCard
          title="Bad Reviews"
          value={reviewsLoading ? "..." : badReviews}
          hint="Ratings at 2 or below that may need follow-up"
          icon={<TriangleAlert size={20} />}
          tone="border-rose-200 bg-gradient-to-br from-rose-50 via-white to-orange-50"
        />
      </div>

      <section className="rounded-[28px] border border-slate-200 bg-white/90 p-4 shadow-sm backdrop-blur">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center">
          <div className="relative flex-1">
            <Search
              size={16}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by ticket, employee, title, or comment"
              className="w-full rounded-2xl border border-slate-200 bg-slate-50/70 py-3 pl-11 pr-4 text-sm outline-none transition focus:border-blue-300 focus:bg-white focus:ring-4 focus:ring-blue-100"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-slate-600">
              <Filter size={16} className="text-slate-400" />
              <select
                value={ratingFilter}
                onChange={(e) => setRatingFilter(e.target.value)}
                className="bg-transparent outline-none"
              >
                <option value="">All Ratings</option>
                <option value="5">5 Stars</option>
                <option value="4">4 Stars</option>
                <option value="3">3 Stars</option>
                <option value="2">2 Stars</option>
                <option value="1">1 Star</option>
              </select>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-700">
              <span className="font-semibold text-slate-900">
                {filteredReviews.length}
              </span>{" "}
              results
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-700">
              <span className="font-semibold text-slate-900">
                {withComments}
              </span>{" "}
              with comments
            </div>
          </div>
        </div>
      </section>

      <section className="overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-sm">
        {reviewsLoading ? (
          <TableRowsSkeleton columns={7} rows={6} />
        ) : (
          <>
            <div className="border-b border-slate-200 bg-[linear-gradient(180deg,_#ffffff,_#f8fafc)] px-6 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">
                    Review Feed
                  </h2>
                  <p className="text-sm text-slate-500">
                    Read sentiment, comments, and related ticket context in one
                    place.
                  </p>
                </div>
                <div className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-700">
                  <Sparkles size={13} />
                  Sorted by newest feedback
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/70">
                    <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Ticket
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Employee
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Rating
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Severity
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Review
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                      Submitted
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredReviews.map((review) => (
                    <tr
                      key={review.id}
                      className="border-b border-slate-100 align-top transition hover:bg-slate-50/80 last:border-0"
                    >
                      <td className="px-6 py-4">
                        <div className="font-mono text-xs text-slate-500">
                          {review.ticket_id}
                        </div>
                        <div className="mt-1 max-w-[280px] font-semibold text-slate-900">
                          {review.ticket_title || "Untitled ticket"}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-700">
                          {review.user_id}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="rounded-2xl border border-amber-100 bg-amber-50/60 px-3 py-2">
                          <Stars rating={review.rating} />
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <SeverityBadge
                          severity={review.ticket_severity || "unknown"}
                        />
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge status={review.ticket_status || "unknown"} />
                      </td>
                      <td className="px-6 py-4">
                        <div className="max-w-[430px] rounded-2xl border border-slate-200 bg-slate-50/70 px-4 py-3 text-slate-700">
                          {review.comment?.trim() || "No written comment"}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-xs font-medium text-slate-500">
                        {formatDate(review.created_at)}
                      </td>
                    </tr>
                  ))}

                  {filteredReviews.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-6 py-16">
                        <div className="mx-auto max-w-md text-center">
                          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-500">
                            <MessageSquareQuote size={24} />
                          </div>
                          <h3 className="mt-4 text-lg font-semibold text-slate-900">
                            No matching reviews
                          </h3>
                          <p className="mt-2 text-sm leading-6 text-slate-500">
                            Try changing the rating filter or search text. If
                            you are logged in as HR, this can also mean your
                            assigned notification levels do not include the
                            severities for the available reviews.
                          </p>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
