import React from "react";
import { EmptyState } from "../components/empty-state";
import { dlgWindow, dlgHeading, dlgInput, dlgPrimary, dlgCancel } from "../components/dialog-styles"
import { pageShell, formCard } from "../components/layout-styles"
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

// How a breakout group is composed and which laptop records what. The join
// page turns this into the slots a device can occupy ("Table 3 · Pat's
// team"), names the pod after its slot and pre-creates its speaker cards.
function PodSetupSection({ setup, setSetup }) {
  const s = setup || {};
  const set = (patch) => setSetup({ ...s, ...patch });
  const setTeam = (i, patch) =>
    set({ teams: s.teams.map((t, j) => (j === i ? { ...t, ...patch } : t)) });
  const int = (v, lo, hi) => Math.max(lo, Math.min(hi, parseInt(v, 10) || lo));
  const groupSize = s.teamsPerGroup === 2 ? s.teams[0].size + s.teams[1].size : s.groupSize;
  const labels = (n, prefix) => {
    const p = (prefix || "Table").trim() || "Table";
    if (n <= 3) return Array.from({ length: n }, (_, i) => `${p} ${i + 1}`).join(", ");
    return `${p} 1, ${p} 2 … ${p} ${n}`;
  };
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
            Set up the groups and laptops in advance
          </span>
          <span className="block text-xs text-tiilt-muted">
            Joining laptops pick their table and team from a list, are named
            after it, and start with the right number of speaker cards. Off:
            groups name themselves and size their roster when they join.
          </span>
        </span>
      </label>
      {s.enabled ? (
        <div className="mt-2 flex flex-col gap-3 rounded-lg border border-tiilt-line bg-white px-3 py-3 text-sm text-tiilt-ink">
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 text-xs text-tiilt-muted">
              Number of groups
              <input
                id="podGroupCount"
                type="number"
                min={1}
                max={200}
                value={s.groupCount}
                onChange={(e) => set({ groupCount: int(e.target.value, 1, 200) })}
                className={numberCls}
              />
            </label>
            <label className="flex grow flex-col gap-1 text-xs text-tiilt-muted">
              Called
              <input
                id="podGroupPrefix"
                type="text"
                maxLength={28}
                value={s.groupPrefix}
                onChange={(e) => set({ groupPrefix: e.target.value })}
                className={textCls}
                placeholder="Table"
              />
            </label>
            <span className="pb-2 text-xs text-tiilt-muted">{labels(s.groupCount, s.groupPrefix)}</span>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 text-xs text-tiilt-muted">
              Teams per group
              <select
                id="podTeamsPerGroup"
                value={s.teamsPerGroup}
                onChange={(e) => set({ teamsPerGroup: parseInt(e.target.value, 10) })}
                className={numberCls + " app-select w-28 cursor-pointer pr-7"}
              >
                <option value={1}>No teams</option>
                <option value={2}>Two teams</option>
              </select>
            </label>
            {s.teamsPerGroup === 2 ? (
              s.teams.slice(0, 2).map((t, i) => (
                <div key={i} className="flex items-end gap-2">
                  <label className="flex flex-col gap-1 text-xs text-tiilt-muted">
                    Team {i + 1}
                    <input
                      id={`podTeamName${i}`}
                      type="text"
                      maxLength={16}
                      value={t.name}
                      onChange={(e) => setTeam(i, { name: e.target.value })}
                      className={textCls + " w-28"}
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-tiilt-muted">
                    People
                    <input
                      id={`podTeamSize${i}`}
                      type="number"
                      min={1}
                      max={32}
                      value={t.size}
                      onChange={(e) => setTeam(i, { size: int(e.target.value, 1, 32) })}
                      className={numberCls + " w-16"}
                    />
                  </label>
                </div>
              ))
            ) : (
              <label className="flex flex-col gap-1 text-xs text-tiilt-muted">
                People per group
                <input
                  id="podGroupSize"
                  type="number"
                  min={1}
                  max={64}
                  value={s.groupSize}
                  onChange={(e) => set({ groupSize: int(e.target.value, 1, 64) })}
                  className={numberCls}
                />
              </label>
            )}
            <span className="pb-2 text-xs text-tiilt-muted">
              {s.groupCount} {s.groupCount === 1 ? "group" : "groups"} of {groupSize}
              {s.teamsPerGroup === 2 ? ` (${s.teams[0].name || "Team 1"} ${s.teams[0].size} vs ${s.teams[1].name || "Team 2"} ${s.teams[1].size})` : ""}
            </span>
          </div>
          {s.teamsPerGroup === 2 ? (
            <div className="flex flex-col gap-1.5">
              <span className="text-xs text-tiilt-muted">Laptops</span>
              {[
                ["group", "One laptop per group", "One microphone and camera for the whole table."],
                ["team", "One laptop per team", "Each team joins from its own laptop and picks its table and team; everything that laptop hears and sees counts for that team."],
              ].map(([value, title, desc]) => (
                <label key={value} htmlFor={`podDevices-${value}`} className="flex cursor-pointer items-start gap-3">
                  <input
                    id={`podDevices-${value}`}
                    type="radio"
                    name="podDevices"
                    className="mt-0.5 h-4 w-4 flex-none cursor-pointer accent-tiilt"
                    checked={s.devices === value}
                    onChange={() => set({ devices: value })}
                  />
                  <span>
                    <span className="block text-sm text-tiilt-ink">{title}</span>
                    <span className="block text-xs text-tiilt-muted">{desc}</span>
                  </span>
                </label>
              ))}
            </div>
          ) : null}
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
              <PodSetupSection setup={props.podSetup} setSetup={props.setPodSetup} />
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
                      up per team (Pat vs Sandy) on the pod page.
                    </span>
                  </span>
                </label>
                {props.negotiationCoding === true ? (
                  <p className="mt-2 text-xs text-tiilt-muted">
                    {props.negotiationPaired
                      ? "Teams come from the pod setup above: each team records from its own laptop, and the two laptops of a table are coded as one negotiation."
                      : "With one laptop per table you assign each speaker to a team by name on the pod page after the session. Set up pods above with two teams and one laptop per team to have the teams fixed by device instead."}
                  </p>
                ) : null}
              </div>
            </div>
            <div className={footerBar}>
              <div className={footerRow}>
                <button
                  className={dlgPrimary + " w-full"}
                  onClick={props.createSession}
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
                  onClick={props.createSession}
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
