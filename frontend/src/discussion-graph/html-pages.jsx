import React from 'react'
import { GenericDialogBox } from '../dialog/dialog-component'
import { Appheader } from '../header/header-component'
import { SessionTabs } from '../components/session-tabs'
import { dlgHeading, dlgBody, btnPrimarySm, btnSecondary } from '../components/dialog-styles'

// Vertical pixels per second of conversation. The timeline ruler and the
// transcript blocks share it, so a block's top edge always lines up with its
// start time on the ruler.
const PX_PER_SEC = 20
const TIMESTAMP_STEP_SEC = 5

function ColumnHeader({ device, onOpenStats }) {
    return (
        <button
            type="button"
            onClick={() => onOpenStats(device)}
            title={`Statistics for ${device.name}`}
            className="w-full cursor-pointer truncate rounded-lg px-3 py-2 text-sm font-semibold text-tiilt-ink transition hover:bg-tiilt-soft hover:text-tiilt"
        >
            {device.name}
        </button>
    )
}

// One pod's column. Blocks are positioned absolutely from their start time —
// the old markup pushed them with margin-top, which stacks in normal flow, so
// each line drifted further past its real position the longer a session ran.
function TranscriptColumn({ device, height, onHighlight, onOpenKeywords }) {
    return (
        <div
            className="relative min-w-[250px] flex-1 border-l border-tiilt-line"
            style={{ height: `${height}px` }}
        >
            {device.transcripts.map((transcript, index) => (
                <div
                    key={index}
                    className="absolute right-1 left-1 overflow-hidden rounded-lg border border-tiilt-line bg-white px-2 py-1 text-[13px] leading-snug text-tiilt-ink shadow-sm"
                    style={{
                        top: `${transcript.start_time * PX_PER_SEC}px`,
                        minHeight: `${Math.max(transcript.length * PX_PER_SEC, 24)}px`,
                    }}
                >
                    {transcript.question ? (
                        <button
                            type="button"
                            aria-label="Highlight this question"
                            onClick={() => onHighlight(transcript)}
                            className="mr-1 cursor-pointer rounded bg-tiilt-soft px-1.5 text-xs font-bold text-tiilt hover:bg-tiilt hover:text-white"
                        >
                            ?
                        </button>
                    ) : null}
                    {transcript.speaker_tag ? (
                        <span className="font-semibold text-tiilt-muted">
                            {transcript.speaker_tag}:{' '}
                        </span>
                    ) : null}
                    {transcript.transcript.map((word, wordIndex) => (
                        <React.Fragment key={wordIndex}>
                            {word.matchingKeywords !== null ? (
                                <button
                                    type="button"
                                    aria-label={`Keyword details for ${word.word}`}
                                    onClick={() => onOpenKeywords(word.matchingKeywords)}
                                    style={{ color: word.color }}
                                    className={
                                        'inline cursor-pointer p-0 text-left font-semibold underline decoration-dotted ' +
                                        (word.highlight ? 'bg-tiilt-orange/20' : '')
                                    }
                                >
                                    {word.word}
                                </button>
                            ) : (
                                <span className={word.highlight ? 'bg-tiilt-orange/20' : ''}>
                                    {' '}
                                    {word.word}{' '}
                                </span>
                            )}
                        </React.Fragment>
                    ))}
                </div>
            ))}
        </div>
    )
}

function EmptyState({ message, hint }) {
    return (
        <div className="mx-auto flex max-w-xl flex-col items-center gap-4 rounded-2xl border border-tiilt-line bg-white px-6 py-10 text-center shadow-pop">
            <h2 className="text-lg font-semibold text-tiilt-ink">{message}</h2>
            {hint ? <p className="text-sm text-tiilt-muted">{hint}</p> : null}
        </div>
    )
}

function DiscussionPage(props) {
    const devices = props.checkedDevices()
    const hasGraph = devices.length > 0
    // Tall enough for the last line of the longest column, with a little air.
    const graphHeight =
        Math.max(
            0,
            ...devices.map((d) =>
                d.transcripts.length
                    ? (d.transcripts[d.transcripts.length - 1].start_time +
                          d.transcripts[d.transcripts.length - 1].length) *
                      PX_PER_SEC
                    : 0,
            ),
        ) + 40

    return (
        <>
            <div role="main" className="main-container">
                <Appheader
                    title={'Discussion graph'}
                    leftText={false}
                    rightText={'Groups'}
                    rightTextClick={() => props.openForms('devices')}
                    nav={props.navigateToSession}
                    escToBack={true}
                />
                <SessionTabs />

                <div className="toolbar-view-container">
                    <div className="min-h-0 grow overflow-y-auto">
                        <div className="mx-auto w-full max-w-6xl px-4 py-8 lg:px-8">
                            <div className="mb-4 flex flex-wrap items-start justify-between gap-x-3 gap-y-2">
                                <div>
                                    <h2 className="text-lg font-semibold text-tiilt-ink">
                                        Conversation timeline
                                    </h2>
                                    <p className="text-sm text-tiilt-muted">
                                        Every group on a shared clock. Select a group
                                        name for its statistics, or a highlighted word
                                        for the keywords it matched.
                                    </p>
                                </div>
                            </div>

                            {hasGraph ? (
                                <div className="overflow-hidden rounded-2xl border border-tiilt-line bg-white shadow-pop">
                                    <div className="overflow-x-auto">
                                        <div className="min-w-fit">
                                            {/* Column headers, held above the scroll */}
                                            <div className="sticky top-0 z-10 flex border-b border-tiilt-line bg-tiilt-ground">
                                                <span className="w-[70px] flex-none" />
                                                {devices.map((device, index) => (
                                                    <div
                                                        key={index}
                                                        className="min-w-[250px] flex-1"
                                                    >
                                                        <ColumnHeader
                                                            device={device}
                                                            onOpenStats={(d) =>
                                                                props.openForms('stats', d)
                                                            }
                                                        />
                                                    </div>
                                                ))}
                                            </div>

                                            <div className="flex">
                                                {/* Ruler */}
                                                <div
                                                    className="relative w-[70px] flex-none font-ahamono text-[11px] tabular-nums text-tiilt-muted"
                                                    style={{ height: `${graphHeight}px` }}
                                                >
                                                    {props.timestamps.map((timestamp, index) => (
                                                        <div
                                                            key={index}
                                                            className="absolute right-2"
                                                            style={{
                                                                top: `${index * TIMESTAMP_STEP_SEC * PX_PER_SEC}px`,
                                                            }}
                                                        >
                                                            {timestamp}
                                                        </div>
                                                    ))}
                                                </div>

                                                {devices.map((device, index) => (
                                                    <TranscriptColumn
                                                        key={index}
                                                        device={device}
                                                        height={graphHeight}
                                                        onHighlight={props.highlightQuestions}
                                                        onOpenKeywords={(keywords) =>
                                                            props.openForms('keywords', keywords)
                                                        }
                                                    />
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <EmptyState
                                    message="Nothing to graph yet"
                                    hint="This appears once a group in this session has transcripts. If the session has finished, check that its analysis has run."
                                />
                            )}
                        </div>
                    </div>
                </div>
            </div>

            <GenericDialogBox onClose={props.closeForm} show={props.currentForm !== ''}>
                {props.currentForm === 'keywords' && props.displayKeywords ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Keyword data</div>
                        <div>
                            <span className="font-semibold">Word:</span>{' '}
                            {props.displayKeywords[0].word}
                        </div>
                        <div>
                            <span className="font-semibold">Keywords (similarity):</span>
                        </div>
                        <div className="text-sm text-tiilt-ink">
                            {props.displayKeywords.map((keyword, index) => (
                                <span key={index}>
                                    {keyword.keyword} ({keyword.similarity}%)
                                    {index === props.displayKeywords.length - 1 ? '' : ', '}
                                </span>
                            ))}
                        </div>
                    </div>
                ) : null}

                {props.currentForm === 'stats' ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>
                            Statistics for{' '}
                            {props.selectedDevice !== undefined
                                ? props.selectedDevice.name
                                : ''}
                        </div>

                        <button
                            type="button"
                            className={btnPrimarySm}
                            aria-expanded={!!props.showGraph}
                            onClick={() =>
                                props.toggleGraph(!props.showGraph, props.selectedDevice)
                            }
                        >
                            Contributions: {props.contributions}
                        </button>

                        {props.showGraph ? (
                            <>
                                <div className="relative mx-auto flex h-40 w-40 items-center justify-center">
                                    <svg
                                        viewBox="-1 -1 2 2"
                                        style={{ transform: 'rotate(-90deg)' }}
                                        className="h-40 w-40"
                                    >
                                        {props.checkedDevices().map((device, index) => (
                                            <path
                                                key={index}
                                                d={device.path}
                                                fill={device.color}
                                                role="button"
                                                tabIndex={0}
                                                aria-label={`Show ${device.name}'s share`}
                                                onClick={() => props.toggleGraph(true, device)}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter' || e.key === ' ') {
                                                        e.preventDefault()
                                                        props.toggleGraph(true, device)
                                                    }
                                                }}
                                                stroke="transparent"
                                                className="cursor-pointer"
                                            />
                                        ))}
                                    </svg>
                                    <span className="absolute font-ahamono text-lg font-semibold tabular-nums text-tiilt-ink">
                                        {props.selectedPercent}%
                                    </span>
                                </div>

                                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                                    {props.checkedDevices().map((device, index) => (
                                        <span
                                            key={index}
                                            className="flex items-center gap-1.5"
                                        >
                                            <span
                                                className="inline-block h-3 w-3 flex-none rounded-sm"
                                                style={{ backgroundColor: device.color }}
                                            />
                                            <span
                                                className={
                                                    device.selected
                                                        ? 'font-semibold text-tiilt-ink'
                                                        : 'text-tiilt-muted'
                                                }
                                            >
                                                {device.name}
                                            </span>
                                        </span>
                                    ))}
                                </div>

                                <div className="text-sm text-tiilt-muted">
                                    {props.selectedDevice.name} spoke for{' '}
                                    {props.selectedPercent}% of the total conversation of
                                    displayed groups.
                                </div>
                            </>
                        ) : null}

                        <button
                            type="button"
                            className={btnPrimarySm}
                            aria-expanded={!!props.showQuestions}
                            onClick={props.toggleQuestions}
                        >
                            Questions: {props.displayQuestions.length}
                        </button>

                        {props.showQuestions ? (
                            <div className="flex max-h-56 flex-col gap-1 overflow-y-auto text-sm text-tiilt-ink">
                                {props.displayQuestions.length ? (
                                    props.displayQuestions.map((question, index) => (
                                        <div
                                            key={index}
                                            className="rounded-lg bg-tiilt-ground px-2 py-1"
                                        >
                                            {question}
                                        </div>
                                    ))
                                ) : (
                                    <span className="text-tiilt-muted">
                                        No questions detected for this group.
                                    </span>
                                )}
                            </div>
                        ) : null}
                    </div>
                ) : null}

                {props.currentForm === 'devices' ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Groups shown</div>
                        {props.displayDevices.length ? (
                            props.displayDevices.map((device, index) => (
                                <label
                                    key={index}
                                    className="flex cursor-pointer items-center gap-2 py-1 text-sm text-tiilt-ink"
                                >
                                    <input
                                        type="checkbox"
                                        className="h-4 w-4 cursor-pointer accent-tiilt"
                                        checked={!!device.checked}
                                        onChange={() => props.changeCheck(index)}
                                    />
                                    {device.name}
                                </label>
                            ))
                        ) : (
                            <span className="text-sm text-tiilt-muted">
                                No groups with transcripts yet.
                            </span>
                        )}
                    </div>
                ) : null}

                <button type="button" className={btnSecondary} onClick={props.closeForm}>
                    Close
                </button>
            </GenericDialogBox>
        </>
    )
}

export { DiscussionPage }
