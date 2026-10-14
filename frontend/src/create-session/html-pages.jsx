import React from "react";
import { EmptyState } from "../components/empty-state";
import { dlgWindow, dlgHeading, dlgInput, dlgPrimary, dlgCancel, dlgError } from "../components/dialog-styles"
import { pageShell, formCard } from "../components/layout-styles"
import { setupTeams } from "./pod-setup"
import { Appheader } from "../header/header-component";
import { GenericDialogBox } from "../dialog/dialog-component";
import { AppFolderSelectComponent } from "../components/folder-select/folder-select-component";
import style from "./create-session.module.css";
import openFolderIcon from "../assets/img/open-folder.svg";
import IconPod from "@icons/IconPod";
import LightIcon from "@icons/Light";

// Single-step creation: name/folder/toggles, then Start session.
// (Keyword lists and topic models moved to post-hoc analysis.)

const contentWrap =
  "mx-auto flex w-full max-w-lg grow flex-col gap-4 px-4 py-6";
const fieldLabel = "mb-1.5 block text-sm font-semibold text-tiilt-ink";
const footerBar = "w-full flex-none border-t border-tiilt-line bg-white";
const footerRow = "mx-auto flex w-full max-w-lg gap-3 px-4 py-4";

const numberCls =
  "h-9 w-20 rounded-lg border border-tiilt-line bg-white px-2 text-sm text-tiilt-ink outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30";
const textCls =
  "h-9 w-full rounded-lg border border-tiilt-line bg-white px-2 text-sm text-tiilt-ink outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30";

// How a breakout group is composed and which device records what. The join
// page turns this into the slots a device can occupy ("Table 3 · <team>'s
// team"), names the pod after its slot and pre-creates its speaker cards.
// Row is module-level (not defined inside the section) so the inputs keep
// focus across re-renders.
function SetupRow({ label, hint, children }) {
  // Label and hint above the controls: the form card is narrow, so side
  // by side would squeeze the inputs.
  return (
    <div className="flex flex-col gap-2 px-4 py-3">
      <div className="flex flex-wrap items-baseline gap-x-2">
        <span className="text-sm font-semibold text-tiilt-ink">{label}</span>
        {hint ? <span className="text-xs text-tiilt-muted">{hint}</span> : null}
      </div>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

const smallLabel = "mb-1 block text-xs text-tiilt-muted";
const teamGrid = "grid grid-cols-[4rem_minmax(0,1fr)_5rem] items-center gap-3";

function PodSetupSection({ setup, setSetup, error }) {
  const s = setup || {};
  const set = (patch) => setSetup({ ...s, ...patch });
  const setTeam = (i, patch) =>
    set({ teams: s.teams.map((t, j) => (j === i ? { ...t, ...patch } : t)) });
  const int = (v, lo, hi) => Math.max(lo, Math.min(hi, parseInt(v, 10) || lo));
  const teams = setupTeams(s);
  const twoTeams = teams.length === 2;
  const hasTeams = teams.length >= 2;
  const groupSize = hasTeams ? teams.reduce((sum, t) => sum + t.size, 0) : s.groupSize;
  const prefix = (s.groupPrefix || "").trim() || "Group";
  const preview =
    s.groupCount <= 3
      ? Array.from({ length: s.groupCount }, (_, i) => `${prefix} ${i + 1}`).join(", ")
      : `${prefix} 1, ${prefix} 2 … ${prefix} ${s.groupCount}`;
  const teamName = (t, i) => (t.name || "").trim() || `Team ${i + 1}`;
  const groupsWord = s.groupCount === 1 ? "group" : "groups";
  const summary = hasTeams
    ? `${s.groupCount} ${groupsWord} of ${groupSize}: ${teams.map((t, i) => `${teamName(t, i)} ${t.size}`).join(" vs ")}, ${twoTeams && s.devices === "team" ? "one device per team" : "one device per group"}.`
    : `${s.groupCount} ${groupsWord} of ${groupSize}, one device per group.`;
  return (
    <div>
      <label className={fieldLabel}>Pod setup</label>
      <label
        htmlFor="chkPodSetup"
        className="flex cursor-pointer items-start gap-3 rounded-lg border border-tiilt-line bg-white px-3 py-2.5"
      >
        <input
          id="chkPodSetup"
          type="checkbox"
          className="mt-0.5 h-4 w-4 flex-none cursor-pointer accent-tiilt"
          checked={s.enabled === true}
          onChange={(event) => set({ enabled: event.target.checked })}
        />
        <span>
          <span className="block text-sm font-semibold text-tiilt-ink">
            Set up the groups and devices in advance
          </span>
          <span className="block text-xs text-tiilt-muted">
            Joining devices pick their group and team from a list, are named
            after it, and start with the right number of speaker cards. Off:
            groups name themselves and size their roster when they join.
          </span>
        </span>
      </label>
      {s.enabled ? (
        <div className="mt-2 divide-y divide-tiilt-line overflow-hidden rounded-lg border border-tiilt-line bg-white">
          <SetupRow label="Groups" hint={preview}>
            <div className="flex flex-wrap items-end gap-3">
              <div>
                <label htmlFor="podGroupCount" className={smallLabel}>
                  How many
                </label>
                <input
                  id="podGroupCount"
                  type="number"
                  min={1}
                  max={200}
                  value={s.groupCount}
                  onChange={(e) => set({ groupCount: int(e.target.value, 1, 200) })}
                  className={numberCls}
                />
              </div>
              <div className="min-w-0 grow basis-40">
                <label htmlFor="podGroupPrefix" className={smallLabel}>
                  Called
                </label>
                <input
                  id="podGroupPrefix"
                  type="text"
                  maxLength={28}
                  value={s.groupPrefix}
                  onChange={(e) => set({ groupPrefix: e.target.value })}
                  className={textCls}
                  placeholder="Table"
                />
              </div>
            </div>
          </SetupRow>

          <SetupRow label="Teams" hint={hasTeams ? "Per group, with how many people on each." : "People per group."}>
            <div className="flex flex-col gap-3">
              <select
                id="podTeamsPerGroup"
                value={s.teamsPerGroup}
                onChange={(e) => set({ teamsPerGroup: parseInt(e.target.value, 10) })}
                className={numberCls + " app-select w-40 cursor-pointer pr-8"}
              >
                <option value={1}>No teams</option>
                <option value={2}>Two teams</option>
                <option value={3}>Three teams</option>
                <option value={4}>Four teams</option>
              </select>
              {hasTeams ? (
                <div className="overflow-hidden rounded-lg border border-tiilt-line">
                  <div className={teamGrid + " bg-tiilt-ground/60 px-3 py-1.5 font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase"}>
                    <span />
                    <span>Name</span>
                    <span>People</span>
                  </div>
                  {teams.map((t, i) => (
                    <div key={i} className={teamGrid + " border-t border-tiilt-line px-3 py-2"}>
                      <label htmlFor={`podTeamName${i}`} className="text-sm text-tiilt-ink">
                        Team {i + 1}
                      </label>
                      <input
                        id={`podTeamName${i}`}
                        type="text"
                        maxLength={16}
                        value={t.name}
                        placeholder={`Team ${"ABCD"[i]}`}
                        onChange={(e) => setTeam(i, { name: e.target.value })}
                        className={textCls}
                      />
                      <input
                        id={`podTeamSize${i}`}
                        type="number"
                        min={1}
                        max={32}
                        aria-label={`People on team ${i + 1}`}
                        value={t.size}
                        onChange={(e) => setTeam(i, { size: int(e.target.value, 1, 32) })}
                        className={numberCls + " w-full"}
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <div>
                  <label htmlFor="podGroupSize" className={smallLabel}>
                    People per group
                  </label>
                  <input
                    id="podGroupSize"
                    type="number"
                    min={1}
                    max={64}
                    value={s.groupSize}
                    onChange={(e) => set({ groupSize: int(e.target.value, 1, 64) })}
                    className={numberCls}
                  />
                </div>
              )}
            </div>
          </SetupRow>

          <SetupRow label="Devices" hint={twoTeams ? "Which device records whom." : hasTeams ? "One device records the whole group (one device per team needs exactly two teams)." : "One device records the whole group."}>
            {twoTeams ? (
              <div className="flex flex-col gap-2">
                {[
                  ["group", "One device per group", "One microphone and camera for the whole table."],
                  ["team", "One device per team", "Each team joins from its own device and picks its table and team; everything that device hears and sees counts for that team."],
                ].map(([value, title, desc]) => (
                  <label
                    key={value}
                    htmlFor={`podDevices-${value}`}
                    className={
                      "flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2 transition " +
                      (s.devices === value ? "border-tiilt bg-tiilt-soft/60" : "border-tiilt-line bg-white hover:bg-tiilt-soft/30")
                    }
                  >
                    <input
                      id={`podDevices-${value}`}
                      type="radio"
                      name="podDevices"
                      className="mt-0.5 h-4 w-4 flex-none cursor-pointer accent-tiilt"
                      checked={s.devices === value}
                      onChange={() => set({ devices: value })}
                    />
                    <span>
                      <span className="block text-sm font-semibold text-tiilt-ink">{title}</span>
                      <span className="block text-xs text-tiilt-muted">{desc}</span>
                    </span>
                  </label>
                ))}
              </div>
            ) : (
              <div className="pt-2 text-sm text-tiilt-ink">One device per group</div>
            )}
          </SetupRow>

          <div className="bg-tiilt-ground/40 px-4 py-2.5 text-xs text-tiilt-ink">
            {summary}
            {error ? <div className={dlgError + " mt-1"}>{error}</div> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function CreateSessionPage(props) {
  return (
    <>
      <div role="main" className="main-container">
        <Appheader
          title={props.pageTitle}
          leftText={false}
          rightText={""}
          nav={props.navigateToSessions}
        />
        <div className={pageShell}>
        <div className={formCard}>

        {props.currentMenu === "Settings" ? (
          <React.Fragment>
            <div className={contentWrap}>
              <div>
                <label htmlFor="txtName" className={fieldLabel}>
                  Session name
                </label>
                <input
                  id="txtName"
                  className={dlgInput}
                  defaultValue={props.sessionName}
                  onInput={(event) => props.setSessionName(event.target.value)}
                  maxLength="64"
                  placeholder="Untitled session"
                />
              </div>
              <div>
                <label className={fieldLabel}>Folder</label>
                <button
                  type="button"
                  onClick={() => props.openDialog("Folder", "test")}
                  className="flex h-11 w-full items-center justify-between gap-2 rounded-lg border border-tiilt-line bg-white px-3 text-left text-base text-tiilt-ink transition hover:border-tiilt"
                >
                  <span className="truncate">{props.folderPath || "Home"}</span>
                  <img src={openFolderIcon} alt="" className="h-5 w-5 flex-none" />
                </button>
              </div>
              <div>
                <label className={fieldLabel}>Live transcription</label>
                <div className="divide-y divide-tiilt-line overflow-hidden rounded-lg border border-tiilt-line">
                  {/* CrisperWhisper is the only engine (Google Cloud Speech was
                      removed): shown as a single locked choice so it stays
                      explicit what transcribes the session. */}
                  {[
                    {
                      value: "crisperwhisper",
                      name: "CrisperWhisper 2.0 — verbatim, on this server",
                      desc: "Keeps fillers, stutters and false starts with pause-accurate word timing. Audio never leaves the machine; captions run a few seconds behind.",
                    },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => props.setAsr(opt.value)}
                      aria-pressed={props.asr === opt.value}
                      className={
                        "flex w-full items-start gap-3 px-3 py-2.5 text-left transition " +
                        (props.asr === opt.value
                          ? "bg-tiilt-soft"
                          : "bg-white hover:bg-tiilt-soft/40")
                      }
                    >
                      <span
                        className={
                          "mt-1 h-3.5 w-3.5 flex-none rounded-full border-2 " +
                          (props.asr === opt.value
                            ? "border-tiilt bg-tiilt"
                            : "border-tiilt-line")
                        }
                        aria-hidden="true"
                      />
                      <span>
                        <span className="block text-sm font-semibold text-tiilt-ink">
                          {opt.name}
                        </span>
                        <span className="block text-xs text-tiilt-muted">
                          {opt.desc}
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
                <p className="mt-1 text-xs text-tiilt-muted">
                  Locked once the session starts.
                </p>
              </div>
              <div>
                <label className={fieldLabel}>Video</label>
                <label
                  htmlFor="chkLiveVideoAnalytics"
                  className="flex cursor-pointer items-start gap-3 rounded-lg border border-tiilt-line bg-white px-3 py-2.5"
                >
                  <input
                    id="chkLiveVideoAnalytics"
                    type="checkbox"
                    className="mt-0.5 h-4 w-4 flex-none cursor-pointer accent-tiilt"
                    checked={props.liveVideoAnalytics !== false}
                    onChange={(event) =>
                      props.setLiveVideoAnalytics(event.target.checked)
                    }
                  />
                  <span>
                    <span className="block text-sm font-semibold text-tiilt-ink">
                      Analyse video live (uses the GPU during class; off = record now, analyse after class)
                    </span>
                    <span className="block text-xs text-tiilt-muted">
                      Off: every group&apos;s video is still recorded, and the
                      attention and emotion analysis is queued automatically
                      when the session ends.
                    </span>
                  </span>
                </label>
              </div>
              <PodSetupSection setup={props.podSetup} setSetup={props.setPodSetup} error={props.podSetupError} />
              <div>
                <label className={fieldLabel}>Negotiation coding</label>
                <label
                  htmlFor="chkNegotiationCoding"
                  className="flex cursor-pointer items-start gap-3 rounded-lg border border-tiilt-line bg-white px-3 py-2.5"
                >
                  <input
                    id="chkNegotiationCoding"
                    type="checkbox"
                    className="mt-0.5 h-4 w-4 flex-none cursor-pointer accent-tiilt"
                    checked={props.negotiationCoding === true}
                    onChange={(event) =>
                      props.setNegotiationCoding(event.target.checked)
                    }
                  />
                  <span>
                    <span className="block text-sm font-semibold text-tiilt-ink">
                      Negotiation coding (Viking case: code utterances per team after each pod finishes)
                    </span>
                    <span className="block text-xs text-tiilt-muted">
                      A local model codes each utterance for emotion,
                      interests/rights/power, frame and listening moves, rolled
                      up per team (the teams named in the pod setup) on the pod page.
                    </span>
                  </span>
                </label>
                {props.negotiationCoding === true ? (
                  <p className="mt-2 text-xs text-tiilt-muted">
                    {props.negotiationPaired
                      ? "Teams come from the pod setup above: each team records from its own device, and the two devices of a table are coded as one negotiation."
                      : "With one device per group you assign each speaker to a team by name on the pod page after the session. Set up pods above with two teams and one device per team to have the teams fixed by device instead."}
                  </p>
                ) : null}
              </div>
            </div>
            <div className={footerBar}>
              <div className={footerRow}>
                <button
                  className={dlgPrimary + " w-full"}
                  onClick={props.createSession} disabled={!!props.podSetupError}
                >
                  Start session
                </button>
              </div>
            </div>
            <div className="mx-auto w-full max-w-lg flex-none px-4 pb-4 text-center text-xs text-tiilt-muted">
              Keywords and topic models are chosen later, as part of
              post-hoc analysis on each pod.
            </div>
          </React.Fragment>
        ) : (
          <></>
        )}

        {props.currentMenu === "Devices" ? (
          <React.Fragment>
            <div className={contentWrap}>
              {props.devices.length === 0 ? (
                <EmptyState
                  title="No devices"
                  subtitle="No participant devices have joined yet."
                />
              ) : (
                <></>
              )}
              {props.devices.length > 0 ? (
                <ul className={style.list}>
                  {props.devices.map((device) => {
                    <li
                      className={
                        props.selectedDevices.includes(device)
                          ? style["selected-pod"]
                          : style["pod-item"]
                      }
                      onClick={() => props.deviceSelected(device)}
                    >
                      <IconPod className={style["pod-icon"]} aria-hidden="true" />
                      <div className={style["pod-text"]}>{device.name}</div>
                      <div className={style["button-container"]}>
                        <button
                          aria-label={`Blink light on ${device.name || "pod"}`}
                          aria-pressed={!!device.blinking}
                          className={
                            device.blinking
                              ? style["selected-button"]
                              : style["pod-button"]
                          }
                          onClick={(event) => props.blinkPod(event, device)}
                        >
                          <svg
                            x="0"
                            y="0"
                            width="20"
                            height="20"
                            viewBox="0 0 512 512"
                            className={style["light-svg"]}
                          >
                            <LightIcon></LightIcon>
                          </svg>
                        </button>
                      </div>
                    </li>;
                  })}
                </ul>
              ) : (
                <></>
              )}
              <button
                className={dlgCancel + " w-full"}
                onClick={props.onClickSelectAll}
              >
                Select all
              </button>
            </div>
            <div className={footerBar}>
              <div className={footerRow}>
                <button
                  className={dlgCancel + " flex-1"}
                  onClick={props.goToSettings}
                >
                  Previous
                </button>
                <button
                  className={dlgPrimary + " flex-1"}
                  onClick={props.createSession} disabled={!!props.podSetupError}
                >
                  Start session
                </button>
              </div>
            </div>
          </React.Fragment>
        ) : (
          <></>
        )}
        </div>
        </div>
      </div>

      <GenericDialogBox onClose={props.closeDialog} show={props.currentForm !== ""}>
        {props.currentForm === "Error" ? (
          <div className={dlgWindow}>
            <div className={dlgHeading}>Invalid Session</div>
            <div className="text-sm text-tiilt-ink">{props.displayText}</div>
            <button className={dlgCancel} onClick={props.closeDialog}>
              Close
            </button>
          </div>
        ) : (
          <></>
        )}

        {props.currentForm === "Folder" ? (
          <div className={dlgWindow}>
            <div className={dlgHeading}>Select folder</div>
            <AppFolderSelectComponent
              selectableFolders={props.folders}
              setFolderSelect={props.setFolderSelect}
              setBreadCrumbSelect={props.setBreadCrumbSelect}
            />
            {props.folderSelect ? (
              <button
                className={dlgPrimary}
                onClick={() =>
                  props.setFolderLocation(
                    props.folderSelect,
                    props.breadCrumbSelect
                  )
                }
              >
                OK
              </button>
            ) : (
              <></>
            )}
            <button className={dlgCancel} onClick={props.closeDialog}>
              Cancel
            </button>
          </div>
        ) : (
          <></>
        )}
      </GenericDialogBox>
    </>
  );
}

export { CreateSessionPage };
