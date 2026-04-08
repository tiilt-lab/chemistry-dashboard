import { motion } from "framer-motion";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {  CheckCircle2} from "lucide-react";


function SurveyCompletion(props) {
    const allComplete = props.completedCount === props.surveyquestion?.length && props.notes !== "";

    return (
        <div className="w-full ">

                  <motion.div
                    initial={{ opacity: 0, x: 16 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.35 }}
                    className="w-full"
                  >
                    <Card className="h-full border shadow-sm">
                      <CardHeader className="space-y-3 border-b bg-white rounded-t-2xl">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <CardTitle className="text-xl font-semibold">
                              Survey Questions
                            </CardTitle>
                            <CardDescription className="text-lg  leading-6">
                              Reflect on your collaboration experience and provide answers to the following questions (survey should only take about 1-2 mins)
                            </CardDescription>
                          </div>
                          <Badge variant="secondary" className="rounded-full px-3 py-1 text-xs">
                            {props.completedCount}/{props.surveyquestion.length} completed
                          </Badge>
                        </div>

                      </CardHeader>
                      <CardContent className="space-y-6 p-4 md:p-6 overflow-y-auto">
                        <div className="space-y-5">
                          {props.surveyquestion.map((question, index) => (
                            <motion.div
                              key={question[0]}
                              initial={{ opacity: 0, y: 10 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ delay: index * 0.04 }}
                              className="rounded-2xl border bg-white p-4 shadow-sm"
                            >
                              {/* <div className="mb-3 flex items-center justify-between gap-3">
                                    <Label className="text-sm font-medium leading-5 text-slate-900">
                                      {index + 1 + ". " + criterion[0]}
                                    </Label>
                                    <span className="text-xs text-slate-500">1 = strongly disagree, 5 = strongly agree</span>
                                  </div> */}
                              <div className="mt-2 text-lg font-semibold">{index + 1 + ". " + question[1]} {question.length === 3 && (<><br /><i>{question[2]} </i></>)}</div>
                              <div className="grid grid-cols-5 gap-2">
                                {props.likertOptions[index].map((value) => {
                                  const active = props.ratings[question[0]] === value;
                                  return (
                                    <button
                                      key={value}
                                      type="button"
                                      onClick={() => props.handleRate(question[0], value)}
                                      className={`rounded-xl border px-3 py-3 text-sm font-medium transition-all ${active
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
                          <Label className="text-lg font-semibold" htmlFor="notes">What role(s) do you find yourself playing in this group collaborations? And what would you do to make the collaboration experience better?</Label>
                          <Textarea
                            id="notes"
                            placeholder="Open ended response"
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
                            Submit response
                          </Button>

                          {!allComplete && (
                            <p className="text-sm text-slate-500">
                              Please complete all survey questions before submitting.
                            </p>
                          )}

                          {props.submitted && (
                            <div className="flex items-center gap-2 rounded-2xl border bg-white px-4 py-3 text-sm text-slate-700">
                              <CheckCircle2 className="h-4 w-4" />
                              Survey Responses captured successfully.
                            </div>
                          )}
                        </div>
                      </CardContent>

                    </Card>
                  </motion.div>

                </div>
    )
}

export {SurveyCompletion}