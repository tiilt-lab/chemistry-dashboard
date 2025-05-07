import backicon from "../assets/img/icon-back.svg"

function Appheader(props) {
    return (
        <div className="relative top-0 z-10 flex h-12 w-full flex-none flex-row items-center bg-[#FCFDFF] shadow m-h-1/12">
            {props.leftText !== false ? (
                <div onClick={props.nav} className="text-sans w-min p-4">
                    {" "}
                    {props.leftText}
                </div>
            ) : (
                <img
                    onClick={props.nav}
                    alt="back"
                    className={"w-min p-4"}
                    src={backicon}
                />
            )}
            <div className="text-sans w-full overflow-hidden text-center leading-14 whitespace-nowrap select-none">
                {props.editMode ? (
                    <input
                        class="visible w-52 overflow-scroll border-0 leading-14"
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
                className="text-sans w-max px-3 text-center leading-14 disabled:text-gray-50"
            >
                {props.rightText}
            </div>
        </div>
    )
}

export { Appheader }
