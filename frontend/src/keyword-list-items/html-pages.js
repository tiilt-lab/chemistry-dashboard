
import './keyword-list-items-component.scss';
import {Appheader} from '../header/header-component';
import removeicon from '../assets/img/remove.svg'

function KeywordListPages(props){
  const showLoading = () => {
    if (!props.keywordList) {
        return <div className="load-text onload">Loading...</div>
    }
  }
  const emptykeyword = ()=>{
    if(props.keywordListItems && props.keywordListItems.length === 0){
    return(
      <div className="empty-keyword-list" >
        <div className="load-text">Type a title for your list and click Add Keyword below to add keywords.</div>
      </div>
    )
    }
  }
  
  const displayKeywordList = ()=>{
    //console.log(props.keywordListItems, "inside for")
    let comps = []
    let count  = 1
    let val = ''
    for (const keyword of props.keywordListItems) {
      val = keyword.keyword === undefined?'':keyword.keyword
      comps.push(
        <div key={"keyword"+count}  className="change-keywords-container">
        <input  touched="true"  type="text" defaultValue={val} autoComplete="off" onKeyUp={(event)=> props.checkKeyword(keyword,event)} maxLength='64' />
        <img  alt='remove' width='16' height='16' src={removeicon} onClick={() => props.removeKeyword(keyword)} />
        {(keyword.error != null && props.keywordError!=="") ? <div  className="add-new-keywords-status">{props.keywordError}</div> : <></> }
        </div>);
        count = count + 1;
    }
    return comps
  }
  
  const displayKeyword = ()=>{
    
    if(props.keywordList && props.keywordListItems){
      const val = props.keywordList.name === undefined?'':props.keywordList.name
      return(
        <>
        {showLoading()}
        {emptykeyword()} 
        <input className="keyword-lists-title" defaultValue={val} placeholder="Enter new list name" maxLength='64'  type="text"  onKeyUp={props.checkName} />
      <div className="keyword-lists-container">
        {displayKeywordList()}
      </div>
      <button className="basic-button medium-button" onClick={props.addNewKeyword}>Add Keyword</button>
       </> 
      )
    }
  }

  return(
    <div className="container">
      <Appheader 
          title={"Manage Keyword Lists"} 
          leftText = {"Cancel"}
          rightText = {"Save"}
          rightEnabled = {props.isValid}
          rightTextClick = {props.saveKeywordList}
          nav={props.navigate}
           />
        {displayKeyword()}    
    </div>
  )
}

export {KeywordListPages}

  
  

