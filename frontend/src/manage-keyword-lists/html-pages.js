import { AppContextMenu } from '../components/context-menu/context-menu-component';
import { DialogBoxTwoOption } from '../dialog/dialog-component';
import { Appheader } from '../header/header-component';
import style from './manage-keyword-lists.module.css'
import style2 from '../components/context-menu/context-menu.module.css'
import { isLargeScreen } from '../myhooks/custom-hooks';

function KeywordListPage(props) {

    const actualKeywordList = props.keywordLists !== undefined ? props.keywordLists : [];
    return (
        <>
            <div className={style.container}>
                <Appheader
                    title={"Manage Keyword Lists"}
                    leftText={false}
                    rightText={""}
                    rightEnabled={false}
                    nav={props.navigate} />
                <div className={style["list-container" ]}>
                    {(!props.keywordLists) ? <div className={style["load-text onload"]}>Loading...</div> : <></>}
                    {(props.keywordLists && props.keywordLists.length === 0) ?

                        <div className={style["empty-keyword-list"]}>
                            <div className={style["load-text"]}> No Keyword Lists </div>
                            <div className={style["load-text-description"]}> Tap the button below to make your first keyword list. </div>
                        </div>
                        :
                        <></>}
                    {props.keywordLists.map((keywordList, count) => (
                        <div key={"keyword" + count} className={style["keyword-list-button"]} >
                            <div className={style["click-mask"]} onClick={() => { props.keywordListClicked(keywordList) }} ></div >
                            <div className={style["keyword-list-header"]}>
                                <div className={style.title}>{keywordList.name}</div>
                                <div className={style.date}>{props.formatdate(keywordList.creation_date)}</div>
                            </div>
                            <div className={style["keyword-list-keywords"]}>{keywordList.keywords.join(", ")}</div>
                            <AppContextMenu className={style["keyword-list-options"]}>
                                <div className={`${style2["menu-item"]} ${style2["red"]}`} onClick={() => { props.deleteKeywordList(keywordList) }}>Delete</div>
                            </AppContextMenu >
                        </div>
                    ))}
                    {/* {displayKeywordList()} */}
                </div>
                <div>
                  <button className={isLargeScreen() ? `${style["basic-button"]} ${style["medium-button"]}` : `${style["basic-button"]} ${style["small-button"]}`} onClick={props.openNewKeywordList} > New Keyword List</button >
                </div>
                <div>
                  <button className={isLargeScreen() ? `${style["basic-button"]} ${style["medium-button"]}` : `${style["basic-button"]} ${style["small-button"]}`} onClick={props.createTopicModel}> Create Topic Model</button >
                </div>

            </div>

            <DialogBoxTwoOption
                show={props.deleteDialogIsOpen}
                itsclass = {style["dialog-window"]}
                heading={"Delete Keyword List"}
                body={"Are you sure you want to permanently delete this keyword list?"}
                deletebuttonaction={props.confirmDeleteKeywordList}
                cancelbuttonaction={props.closeDeleteDialog}
            />
        </>
    )
}

export { KeywordListPage }
