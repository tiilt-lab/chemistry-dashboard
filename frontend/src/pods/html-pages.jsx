import { dlgWindow, dlgHeading, dlgInput, dlgPrimary, dlgCancel } from '../components/dialog-styles'
import { EmptyState } from "../components/empty-state";
import { pageShell, formCard } from '../components/layout-styles'
import { AppContextMenu } from '../components/context-menu/context-menu-component'
import { Appheader } from '../header/header-component'
import { GenericDialogBox } from '../dialog/dialog-component'
import IconPod from "../Icons/IconPod"
import LightIcon from "../Icons/Light"
import React from 'react'

const dlgDanger =
  "mt-2 h-11 rounded-lg bg-tiilt-danger font-semibold text-white transition hover:opacity-90 active:translate-y-px"

function PodComponentPage(props) {
  const isAdmin = props.user.isAdmin || props.user.isSuper

  return (
    <>
      <div role="main" className="main-container">
        <Appheader
          title={"Devices"}
          leftText={false}
          nav={props.navigateToHomescreen}
        />

        <div className={pageShell}>
        <div className={formCard}>
        <div className="mx-auto flex w-full max-w-lg grow flex-col gap-4 px-4 py-6">
          {props.devices === undefined ? (
            <div className="py-10 text-center text-sm text-tiilt-muted">
              Loading…
            </div>
          ) : props.devices.length === 0 ? (
            <EmptyState
              title="There are no devices"
              subtitle="Add a device with the button below."
            />
          ) : (
            <ul className="flex flex-col gap-2">
              {props.devices.map((device, index) => (
                <li
                  key={index}
                  className="flex items-center gap-3 rounded-lg border border-tiilt-line bg-white px-4 py-3"
                >
                  <IconPod
                    width={20}
                    height={18}
                    fill="currentColor"
                    className={
                      device.connected
                        ? "flex-none text-tiilt-green"
                        : "flex-none text-tiilt-muted"
                    }
                  />
                  <div className="min-w-0 grow">
                    <div className="truncate font-semibold text-tiilt-ink">
                      {device.name}
                    </div>
                    <div
                      className={`text-xs font-medium ${device.connected ? "text-tiilt-green" : "text-tiilt-muted"}`}
                    >
                      {device.connected ? "Online" : "Offline"}
                    </div>
                  </div>
                  {device.connected ? (
                    <button
                      onClick={() => props.blinkPod(device)}
                      title="Blink device"
                      className={`flex h-9 w-9 flex-none items-center justify-center rounded-lg border transition ${device.blinking ? "border-tiilt bg-tiilt-soft text-tiilt" : "border-tiilt-line text-tiilt-muted hover:border-tiilt hover:text-tiilt"}`}
                    >
                      <LightIcon width={20} height={20} fill="currentColor" />
                    </button>
                  ) : (
                    <></>
                  )}
                  <AppContextMenu>
                    <div
                      className="cursor-pointer px-4 py-2 text-sm text-tiilt-ink transition hover:bg-tiilt-soft"
                      onClick={() => props.openDialog("Rename", device)}
                    >
                      Rename
                    </div>
                    {isAdmin ? (
                      <div
                        className="cursor-pointer px-4 py-2 text-sm text-tiilt-danger transition hover:bg-tiilt-soft"
                        onClick={() => props.openDialog("Remove", device)}
                      >
                        Remove
                      </div>
                    ) : (
                      <></>
                    )}
                  </AppContextMenu>
                </li>
              ))}
            </ul>
          )}
        </div>

        {isAdmin ? (
          <div className="w-full flex-none border-t border-tiilt-line bg-white">
            <div className="mx-auto w-full max-w-lg px-4 py-4">
              <button
                className={dlgPrimary + " w-full"}
                onClick={() => props.openDialog("Add")}
              >
                Add via MAC address
              </button>
            </div>
          </div>
        ) : (
          <></>
        )}
        </div>
        </div>
      </div>

      <GenericDialogBox onClose={props.closeDialog} show={props.currentForm !== ""}>
        <div className={dlgWindow} style={{ minWidth: "min(20rem, 76vw)" }}>
          {props.currentForm === "Remove" ? (
            <React.Fragment>
              <div className={dlgHeading}>Remove device</div>
              <div className="text-sm text-tiilt-muted">
                Are you sure you want to remove this device?
              </div>
              <button className={dlgDanger} onClick={props.removeDevice}>
                Remove
              </button>
              <button className={dlgCancel} onClick={props.closeDialog}>
                Cancel
              </button>
            </React.Fragment>
          ) : (
            <></>
          )}
          {props.currentForm === "Add" ? (
            <React.Fragment>
              <div className={dlgHeading}>Device MAC address</div>
              <input
                id="macInput"
                className={dlgInput}
                type="text"
                placeholder="00:00:00:00:00:00"
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    props.addDevice(document.getElementById("macInput").value)
                  }
                }}
              />
              <div className="text-sm text-tiilt-danger">{props.statusText}</div>
              <button
                className={dlgPrimary}
                onClick={() =>
                  props.addDevice(document.getElementById("macInput").value)
                }
              >
                Add
              </button>
              <button className={dlgCancel} onClick={props.closeDialog}>
                Cancel
              </button>
            </React.Fragment>
          ) : (
            <></>
          )}
          {props.currentForm === "Rename" ? (
            <React.Fragment>
              <div className={dlgHeading}>Device name</div>
              <input
                id="nameInput"
                className={dlgInput}
                defaultValue={props.selectedDevice.name}
                type="text"
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    props.renameDevice(document.getElementById("nameInput").value)
                  }
                }}
              />
              <div className="text-sm text-tiilt-danger">{props.statusText}</div>
              <button
                className={dlgPrimary}
                onClick={() =>
                  props.renameDevice(document.getElementById("nameInput").value)
                }
              >
                Rename
              </button>
              <button className={dlgCancel} onClick={props.closeDialog}>
                Cancel
              </button>
            </React.Fragment>
          ) : (
            <></>
          )}
        </div>
      </GenericDialogBox>
    </>
  )
}

export { PodComponentPage }
