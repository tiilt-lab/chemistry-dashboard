import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, ChevronRight } from "lucide-react";
import { motion } from "framer-motion";


function LikertRatingInterface(props) {
  const allComplete = props.completedCount === props.evaluationOption.length && props.selectedItemForRating !== -1;
  const isAtStart = props.currentIndex <= 0;
  const isAtEnd = props.currentIndex >= props.itemsForRating.length - 1 || props.itemsForRating.length === 0;

  return (
    <div className="side-bar w-120 bg-slate-50">
      <motion.div
        initial={{ opacity: 0, x: 16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.35 }}
        className="ml-auto h-full w-full max-w-xl"
      >
        <Card className="h-full border shadow-sm">
          <CardHeader className="space-y-3 border-b bg-white rounded-t-2xl">
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle className="text-xl font-semibold">
                  Expert Rating Panel
                </CardTitle>
                <CardDescription className="text-sm  leading-6">
                  Select an option and rate each  <b>1 = Strongly disagree,2 = Disagree, 3 = Neutral, 4 = Agree, 5 = strongly agree.</b>
                </CardDescription>
              </div>
              <Badge variant="secondary" className="rounded-full px-3 py-1 text-xs">
                {props.completedCount}/{props.evaluationOption.length} completed
              </Badge>
            </div>

            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
              <div className="flex items-center gap-2 font-medium text-emerald-800"><CheckCircle2 className="h-4 w-4" />Evaluation Instructions</div>
              <ul className="mt-3 space-y-2 text-sm text-emerald-900/80">
                {props.evaluationOptionInstruction.map((item) => (
                  <li className="flex items-start gap-2"><ChevronRight className="mt-0.5 h-4 w-4" />{item}</li>
                ))}
              </ul>
            </div>

            <div className="flex items-center justify-between gap-3 rounded-2xl border bg-white p-3 shadow-sm">
              <Button
                type="button"
                variant="outline"
                onClick={props.handlePrev}
                disabled={isAtStart}
                className="rounded-xl"
              >
                Prev
              </Button>

              <div className="flex min-w-0 flex-1 flex-col items-center text-center">
                <span className="text-xs text-slate-500">Items to Rate</span>
                <span className="truncate text-sm font-medium text-slate-900">
                  {props.itemsForRating.length > 0 ? `${props.currentIndex + 1} of ${props.itemsForRating.length}` : "No items"}
                </span>
              </div>

              <Button
                type="button"
                variant="outline"
                onClick={props.handleNext}
                disabled={isAtEnd}
                className="rounded-xl"
              >
                Next
              </Button>
            </div>
          </CardHeader>

          {props.selectedItemForRating !== -1 && (
            <CardContent className="space-y-6 p-4 md:p-6 overflow-y-auto">
              <div className="space-y-5">
                {props.evaluationOption.map((criterion, index) => (
                  <motion.div
                    key={criterion[0]}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.04 }}
                    className="rounded-2xl border bg-white p-4 shadow-sm"
                  >
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <Label className="text-sm font-medium leading-5 text-slate-900">
                        {index+1 +". "+ criterion[0]}
                      </Label>
                      <span className="text-xs text-slate-500">1 = strongly disagree, 5 = strongly agree</span>
                    </div>
                    <div className="mt-2 text-sm font-semibold">{criterion[1]}</div>

                    <div className="grid grid-cols-5 gap-2">
                      {props.likertOptions.map((value) => {
                        const active = props.ratings[criterion[0]] === value;
                        return (
                          <button
                            key={value}
                            type="button"
                            onClick={() => props.handleRate(criterion[0], value)}
                            className={`rounded-xl border px-3 py-3 text-sm font-medium transition-all ${active
                              ? "border-transparent bg-tiilt text-white shadow"
                              : "border-slate-200 bg-white hover:border-slate-400"
                              }`}
                            aria-pressed={active}
                          >
                            {value}
                          </button>
                        );
                      })}
                    </div>
                  </motion.div>
                ))}
              </div>

              <div className="space-y-2">
                <Label htmlFor="notes">comments</Label>
                <Textarea
                  id="notes"
                  placeholder="Add any other comments or observations"
                  value={props.notes}
                  onChange={(e) => props.setNotes(e.target.value)}
                  className="min-h-[110px] rounded-2xl bg-white"
                />
              </div>

              <div className="flex flex-col gap-3 pt-2">
                <Button
                  type="submit"
                  disabled={!allComplete}
                  className="w-full rounded-2xl py-6 text-sm font-semibold"
                  onClick={() => props.handleSubmit(allComplete)}
                >
                  Submit ratings
                </Button>

                {!allComplete && (
                  <p className="text-sm text-slate-500">
                    Please select an item and complete all rating categories before submitting.
                  </p>
                )}

                {props.submitted && (
                  <div className="flex items-center gap-2 rounded-2xl border bg-white px-4 py-3 text-sm text-slate-700">
                    <CheckCircle2 className="h-4 w-4" />
                    Ratings captured successfully.
                  </div>
                )}
              </div>
            </CardContent>
          )}
        </Card>
      </motion.div>
    </div>
  );
}

export { LikertRatingInterface }
