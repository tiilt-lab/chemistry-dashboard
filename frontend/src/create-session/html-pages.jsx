import React, { useState } from "react";
import { EmptyState } from "../components/empty-state";
import { dlgWindow, dlgHeading, dlgInput, dlgPrimary, dlgCancel, dlgError } from "../components/dialog-styles"
import { pageShell, formCard } from "../components/layout-styles"
import { setupTeams, MAX_TEAMS, MIN_CUSTOM_TEAMS, deviceTotal } from "./pod-setup"
import { Appheader } from "../header/header-component";
import { GenericDialogBox } from "../dialog/dialog-component";
import { AppFolderSelectComponent } from "../components/folder-select/folder-select-component";
import style from "./create-session.module.css";
import openFolderIcon from "../assets/img/open-folder.svg";
import IconPod from "@icons/IconPod";
import LightIcon from "@icons/Light";

// Single-step creation: name/folder/toggles, then Start session.

const contentWrap =
  "mx-auto flex w-full max-w-lg grow flex-col gap-4 px-4 py-6";
const fieldLabel = "mb-1.5 block text-sm font-semibold text-tiilt-ink";
const footerBar = "w-full flex-none border-t border-tiilt-line bg-white md:rounded-b-2xl";
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
  // Device totals: the session needs this many laptops in the room, so the
  // labels say it outright instead of leaving the multiplication to the
  // instructor ("12 groups, one device per team" is 24 laptops).
  const perGroupTotal = deviceTotal(s.groupCount);
  const perTeamTotal = deviceTotal(s.groupCount * 2);
  const summary = hasTeams
    ? `${s.groupCount} ${groupsWord} of ${groupSize}: ${teams.map((t, i) => `${teamName(t, i)} ${t.size}`).join(" vs ")}, ${twoTeams && s.devices === "team" ? `one device per team ${perTeamTotal}` : `one device per group ${perGroupTotal}`}.`
    : `${s.groupCount} ${groupsWord} of ${groupSize}, one device per group ${perGroupTotal}.`;
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
                  placeholder="Group"
                />
              </div>
            </div>
          </SetupRow>

          <SetupRow label="Teams" hint={hasTeams ? "Per group, with how many people on each." : "People per group."}>
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <select
                  id="podTeamsPerGroup"
                  value={s.teamsPerGroup >= MIN_CUSTOM_TEAMS ? "custom" : s.teamsPerGroup}
                  onChange={(e) =>
                    set({
                      teamsPerGroup:
                        e.target.value === "custom"
                          ? Math.max(MIN_CUSTOM_TEAMS, s.teamsPerGroup)
                          : parseInt(e.target.value, 10),
                    })
                  }
                  className={numberCls + " app-select w-48 cursor-pointer pr-8"}
                >
                  <option value={1}>1 (the whole group)</option>
                  <option value={2}>2</option>
                  <option value="custom">Custom (3 or more)</option>
                </select>
                {s.teamsPerGroup >= MIN_CUSTOM_TEAMS ? (
                  // The count sits on the same line as the select (no
                  // label above it, which would push the row down).
                  <label htmlFor="podTeamsCustom" className="flex items-center gap-2 text-sm text-tiilt-muted">
                    <input
                      id="podTeamsCustom"
                      type="number"
                      min={MIN_CUSTOM_TEAMS}
                      max={MAX_TEAMS}
                      value={s.teamsPerGroup}
                      onChange={(e) => set({ teamsPerGroup: int(e.target.value, MIN_CUSTOM_TEAMS, MAX_TEAMS) })}
                      className={numberCls}
                      aria-label="How many teams per group"
                    />
                    teams
                  </label>
                ) : null}
              </div>
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
                        placeholder={`Team ${"ABCDEFGH"[i]}`}
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
                  ["group", `One device per group ${perGroupTotal}`, "One microphone and camera for the whole table."],
                  ["team", `One device per team ${perTeamTotal}`, "Each team joins from its own device and picks its table and team; everything that device hears and sees counts for that team."],
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
              <div className="pt-2 text-sm text-tiilt-ink">One device per group {perGroupTotal}</div>
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

// Advanced analysis, the last section of the form: which analyses run on
// the video during class. Nothing is on by default; each one costs GPU time
// per pod while the class is on, and whatever is off is still recorded and
// can be run after class from the pod page. (Transcription always runs live
// with CrisperWhisper, so it is not a choice here.)
const LIVE_VIDEO_ANALYSES = [
  { key: "attention", label: "Attention and gaze", desc: "Where each person looks, their attention level and the object of focus." },
  { key: "emotion", label: "Facial emotion", desc: "The expression read from each face." },
];

function AdvancedAnalysisSection({ analyses, toggle }) {
  const chosen = analyses || [];
  const [open, setOpen] = useState(false);
  const summary =
    chosen.length === 0
      ? "Record only; analyse after class"
      : chosen.length === LIVE_VIDEO_ANALYSES.length
        ? "All video analyses live"
        : LIVE_VIDEO_ANALYSES.filter((a) => chosen.includes(a.key)).map((a) => a.label).join(", ") + " live";
  return (
    <div>
      <label className={fieldLabel}>Advanced analysis</label>
      <div className="overflow-hidden rounded-lg border border-tiilt-line bg-white">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          className="flex w-full cursor-pointer items-center justify-between gap-3 px-3 py-2.5 text-left"
        >
          <span>
            <span className="block text-sm font-semibold text-tiilt-ink">Video analysis during class</span>
            <span className="block text-xs text-tiilt-muted">{summary}</span>
          </span>
          <span className="flex-none text-xs text-tiilt-muted">{open ? "Hide" : "Choose"}</span>
        </button>
        {open ? (
          <div className="flex flex-col gap-2 border-t border-tiilt-line px-3 py-2.5">
            {LIVE_VIDEO_ANALYSES.map((a) => (
              <label key={a.key} htmlFor={`chkLive-${a.key}`} className="flex cursor-pointer items-start gap-3">
                <input
                  id={`chkLive-${a.key}`}
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 flex-none cursor-pointer accent-tiilt"
                  checked={chosen.includes(a.key)}
                  onChange={() => toggle(a.key)}
                />
                <span>
                  <span className="block text-sm text-tiilt-ink">{a.label}</span>
                  <span className="block text-xs text-tiilt-muted">{a.desc}</span>
                </span>
              </label>
            ))}
            <p className="text-xs text-tiilt-muted">
              Each live analysis uses the GPU for every group while the class is
              on. Whatever is off is still recorded and can be analysed after
              class from the pod page. Transcription always runs live.
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

// How the devices join: what the join page's "Join with" list opens on.
// Teams can still change it on the day; this only saves the common case
// from a camera-permission prompt (audio classes) or from every team having
// to pick Video by hand (video classes).
const JOIN_MODES = [
  ["audio", "Audio", "Microphone only. No camera permission is asked for."],
  ["video", "Video", "Microphone and camera, for sessions that record or analyse video."],
];

function JoinModeSection({ value, onChange }) {
  return (
    <div>
      <label className={fieldLabel}>Devices join with</label>
      <div className="flex flex-col gap-2">
        {JOIN_MODES.map(([mode, title, desc]) => (
          <label
            key={mode}
            htmlFor={`joinMode-${mode}`}
            className={
              "flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2 transition " +
              (value === mode ? "border-tiilt bg-tiilt-soft/60" : "border-tiilt-line bg-white hover:bg-tiilt-soft/30")
            }
          >
            <input
              id={`joinMode-${mode}`}
              type="radio"
              name="joinMode"
              className="mt-0.5 h-4 w-4 flex-none cursor-pointer accent-tiilt"
              checked={value === mode}
              onChange={() => onChange(mode)}
            />
            <span>
              <span className="block text-sm font-semibold text-tiilt-ink">{title}</span>
              <span className="block text-xs text-tiilt-muted">{desc}</span>
            </span>
          </label>
        ))}
      </div>
      <p className="mt-1.5 text-xs text-tiilt-muted">What the "Join with" list opens on; a team can still change it when joining.</p>
    </div>
  );
}

// Coding: which scheme (Library) codes every utterance after a pod finishes.
function CodingSection({ schemes, value, onChange, paired, goToSchemes }) {
  const list = schemes || [];
  const chosen = list.find((s) => s.ref === value);
  return (
    <div>
      <label htmlFor="selCodingScheme" className={fieldLabel}>
        Coding
      </label>
      <select
        id="selCodingScheme"
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        className="app-select h-11 w-full cursor-pointer rounded-lg border border-tiilt-line bg-white px-3 pr-8 text-base text-tiilt-ink outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
      >
        <option value="">No coding</option>
        {list.map((s) => (
          <option key={s.ref} value={s.ref}>
            {s.name}{s.builtin ? " (built in)" : ""}
          </option>
        ))}
      </select>
      <p className="mt-1 text-xs text-tiilt-muted">
        {chosen
          ? (chosen.description || "") +
            (chosen.description ? " " : "") +
            "After each group finishes, a local model codes every utterance with this scheme; the results roll up per team and per speaker on the pod page."
          : "Pick a coding scheme to have every utterance coded after each group finishes. "}
        {schemes === null ? "Loading schemes…" : null}
        <button type="button" onClick={goToSchemes} className="ml-1 cursor-pointer font-semibold text-tiilt hover:underline">
          Manage coding schemes
        </button>
      </p>
      {chosen ? (
        <p className="mt-1 text-xs text-tiilt-muted">
          {paired
            ? "Teams come from the pod setup above: each team records from its own device, and the two devices of a group are coded as one conversation."
            : "With one device per group you assign each speaker to a team by name on the pod page after the session. Set up pods above with two teams and one device per team to have the teams fixed by device instead."}
        </p>
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
              <PodSetupSection setup={props.podSetup} setSetup={props.setPodSetup} error={props.podSetupError} />
              <JoinModeSection value={props.joinMode} onChange={props.setJoinMode} />
              <CodingSection
                schemes={props.codingSchemes}
                value={props.codingScheme}
                onChange={props.setCodingScheme}
                paired={props.negotiationPaired}
                goToSchemes={props.goToCodingSchemes}
              />
              <AdvancedAnalysisSection
                analyses={props.liveVideoAnalyses}
                toggle={props.toggleLiveVideoAnalysis}
              />
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
