import { AppContextMenu } from '../components/context-menu/context-menu-component';
import { DialogBoxTwoOption } from '../dialog/dialog-component';
import { Appheader } from '../header/header-component';
import './manage-keyword-lists-component.scss'

function KeywordListPage(props) {

    const showLoading = () => {
        if (!props.keywordLists) {
            return <div className="load-text onload">Loading...</div>
        }
    }
    const noKeywordlist = () => {
        if (props.keywordLists && props.keywordLists.length === 0) {
            return (
                <div className="empty-keyword-list">
                    <div className="load-text"> No Keyword Lists </div>
                    <div className="load-text-description"> Tap the button below to make your first keyword list. </div>
                </div>
            )
        }
    }
    const twoOptionDialogBox = ()=>{
        if (props.deleteDialogIsOpen) {
        return (       
            <div className="dialog-window" >
                <div className="dialog-heading">Delete Keyword List</div>
                <div className="dialog-body">Are you sure you want to permanently delete this keyword list?</div>
                <button className="delete-button" onClick={props.confirmDeleteKeywordList} > Yes</button >
                <button className="cancel-button" onClick={props.closeDeleteDialog} > Cancel</button >
            </div>
        )
        }
    }

    const displayKeywordList = () => {
        let comps = []
        let count = 1
        let kws
        for (const keywordList of props.keywordLists) {
            kws = keywordList.keywords.join(", ");
            comps.push(
                <div key={"keyword"+count} className="keyword-list-button" >
                    <div className="click-mask" onClick={() => { props.keywordListClicked(keywordList) }} ></div >
                    <div className="keyword-list-header">
                        <div className="title">{keywordList.name}</div>
                        <div className="date">{props.formatdate(keywordList.creation_date)}</div>
                    </div>
                    <div className="keyword-list-keywords">{kws}</div>
                    <AppContextMenu className="keyword-list-options">
                        <div className="menu-item red" onClick={() => { props.deleteKeywordList(keywordList) }}>Delete</div>
                    </AppContextMenu > 
                </div>
            );
            count = count + 1;
        }
        return comps
    }
    const actualKeywordList = props.keywordLists !== undefined ? props.keywordLists : [];
    return (
        <>
            <div className="container">
                <Appheader
                    title={"Manage Keyword Lists"}
                    leftText={false}
                    rightText={""}
                    rightEnabled={false}
                    nav={props.navigate} />
                <div className="list-container">
                    {showLoading()}
                    {noKeywordlist()}
                    {displayKeywordList()}
                </div>
                <button className="basic-button medium-button" onClick={props.openNewKeywordList} > New Keyword List</button >
                <button className="basic-button medium-button" onClick={props.createTopicModel}> Create Topic Model</button >

            </div>
        
            <DialogBoxTwoOption
                show={props.deleteDialogIsOpen}
                heading={"Delete Keyword List"}
                body={"Are you sure you want to permanently delete this keyword list?"}
                deletebuttonaction={props.confirmDeleteKeywordList}
                cancelbuttonaction={props.closeDeleteDialog}
            />
        </>
    )
}

export { KeywordListPage }