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
import { CheckCircle2 } from "lucide-react";
import { motion } from "framer-motion";


function LikertRatingInterface(props) {
  
  const allComplete = props.completedCount === props.evaluationOption.length && props.selectedItemForRating !== -1;
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
                <CardDescription className="text-sm leading-6">
                  Select an option and rate each dimension on a 5-point Likert scale.
                </CardDescription>
              </div>
              <Badge variant="secondary" className="rounded-full px-3 py-1 text-xs">
                {props.completedCount}/{props.evaluationOption.length} completed
              </Badge>
            </div>

            <div className="space-y-2">
              <Label htmlFor="output-select">Select item to evaluate</Label>
              <Select value={props.selectedItemForRating} onValueChange={props.loadDashboard}>
                <SelectTrigger id="output-select" className="w-full rounded-xl bg-white">
                  <SelectValue placeholder="Choose an dashboard" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={-1}>Choose what to Rate</SelectItem>
                  {props.itemsForRating.map((item, index) => (
                    <SelectItem value={item}>{item}</SelectItem>
                  ))}
                  
                </SelectContent>
              </Select>
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
                            {criterion[0]}
                        </Label>
                        <span className="text-xs text-slate-500">1 = low, 5 = high</span>
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
                                  className={`rounded-xl border px-3 py-3 text-sm font-medium transition-all ${
                                  active
                                      ? "border-slate-900 bg-slate-900 text-white shadow"
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
                    placeholder="Add any notes about the strengths, concerns, or rationale for your ratings..."
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
                    onClick={props.handleSubmit(allComplete)}
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

export {LikertRatingInterface}
