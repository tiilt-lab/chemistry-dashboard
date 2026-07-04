import backicon from "../assets/img/icon-back.svg"

function Appheader(props) {
    return (
        <div className="relative top-0 z-10 flex h-12 w-full flex-none flex-row items-center border-b border-tiilt-line bg-white">
            {props.leftText !== false ? (
                <div
                    onClick={props.nav}
                    className="w-min cursor-pointer p-4 text-sm font-semibold whitespace-nowrap text-tiilt-muted transition hover:text-tiilt"
                >
                    {props.leftText}
                </div>
            ) : (
                <p
                    className="flex w-max cursor-pointer items-center gap-1 p-4 text-sm font-semibold text-tiilt-muted transition hover:text-tiilt"
                    onClick={props.nav}
                >
                    <img alt="" className="h-4 w-4" src={backicon} />
                    Back
                </p>
            )}
            <div className="w-full overflow-hidden text-center text-base leading-12 font-semibold whitespace-nowrap text-tiilt-ink select-none">
                {props.editMode ? (
                    <input
                        className="visible w-52 overflow-scroll border-0 text-center leading-12 outline-none"
                        type="text"
                        defaultValue={props.title}
                        onKeyUp={(event) =>
                            props.changeInputVal(event.target.value)
                        }
                    />
                ) : (
                    props.title
                )}
            </div>
            <div
                onClick={props.rightTextClick}
                className="w-max cursor-pointer px-4 text-center text-sm leading-12 font-semibold whitespace-nowrap text-tiilt transition hover:text-tiilt-deep"
            >
                {props.rightText}
            </div>
        </div>
    )
}

export { Appheader }
