//change the route (both in and out of page)
import { AppContextMenu } from '../components/context-menu/context-menu-component';
import { DialogBoxTwoOption } from '../dialog/dialog-component';
import { Appheader } from '../header/header-component';
import style from './manage-topic-models.module.css';
import style2 from '../components/context-menu/context-menu.module.css';
import { isLargeScreen } from '../myhooks/custom-hooks';

function ManageTopicsPage(props) {

    const actualTopicModels = props.topicModels !== undefined ? props.topicModels : [];
    return (
        <>
            <div className={style.container}>
                <Appheader
                    title={"Manage Topic Models"}
                    leftText={false}
                    rightText={""}
                    rightEnabled={false}
                    nav={props.navigate} />
                <div className={style["list-container" ]}>
                    {(!props.topicModels) ? <div className={style["load-text onload"]}>Loading...</div> : <></>}
                    {(props.topicModels && props.topicModels.length === 0) ?

                        <div className={style["empty-keyword-list"]}>
                            <div className={style["load-text"]}> No Topic Models </div>
                            <div className={style["load-text-description"]}> Tap the button below to make your first topic model. </div>
                        </div>
                        :
                        <></>}
                    {props.topicModels.map((topicModel, count) => (
                        <div key={"keyword" + count} className={style["keyword-list-button"]} >
                            <div className={style["click-mask"]} onClick={() => { props.navTopicList(topicModel.data, topicModel.summary, topicModel.name) }} ></div >
                            <div className={style["keyword-list-header"]}>
                                <div className={style.title}>{topicModel.name}</div>
                                <div className={style.date}>{props.formatdate(topicModel.creation_date)}</div>
                            </div>
                            <div className={style["keyword-list-keywords"]}>{topicModel.summary}</div>
                            <AppContextMenu className={style["keyword-list-options"]}>
                                <div className={`${style2["menu-item"]} ${style2["red"]}`} onClick={() => { props.deleteTopicModel(topicModel) }}>Delete</div>
                            </AppContextMenu >
                        </div>
                    ))}
                    {/* {displayKeywordList()} */}
                </div>
                <div>
                  <button className={isLargeScreen() ? `${style["basic-button"]} ${style["medium-button"]}` : `${style["basic-button"]} ${style["small-button"]}`} onClick={props.navFileUpload}> Create Topic Model</button >
                </div>

            </div>

            <DialogBoxTwoOption
                show={props.deleteDialogIsOpen}
                itsclass = {style["dialog-window"]}
                heading={"Delete Topic Model"}
                body={"Are you sure you want to permanently delete this topic model?"}
                deletebuttonaction={props.confirmDeleteTopicModel}
                cancelbuttonaction={props.closeDeleteDialog}
            />
        </>
    )
}

export { ManageTopicsPage }
