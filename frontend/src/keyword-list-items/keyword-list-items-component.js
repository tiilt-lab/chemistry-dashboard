import { KeywordService } from '../services/keyword-service';
import { KeywordListItemModel } from '../models/keyword-list-item';
import { KeywordListModel } from '../models/keyword-list';
import { useEffect, useState } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { KeywordListPages } from './html-pages'


function KeywordListItemsComponent() {

  const [keywordList, setKeywordList] = useState([]);
  const [keywordListItems, setKeywordListItems] = useState([]);
  const [validName, setValidName] = useState(false);
  const [newPressed, setNewPressed] = useState(false);
  const { keyword_list_id } = useParams();
  const [keywordListID, setKeywordListID] = useState(keyword_list_id);
  const [keyworderror, setKeywordError] = useState("")
  const navigate = useNavigate();
  const location = useLocation();  

  useEffect(() => {
    if (keywordListID !== undefined && keywordListID !== '-1') {
      new KeywordService().getKeywordList(keywordListID).then(response => {
        if (response.status === 200) {
          const data = response.json()
          data.then(
            succ => {
              const result = KeywordListModel.fromJson(succ);
              setKeywordList(result);
              setValidName(true)
            }
          )

        } else {
          console.log("Keyword-items-components func: useEffect 2 ", response)
        }
      },
        apierror => {
          console.log("Keyword-items-components func: useEffect 2 ", apierror)
        });
    } else {
      //console.log("i am inside else")
      setKeywordListID('-1'); // -1 denotes that list is new
      setKeywordList(new KeywordListModel());
      if (keywordList !== null) {
        keywordList.name = null;
        keywordList.id = -1;
      }
      setKeywordListItems([]);
    }
  }, [])

  useEffect(() => {
    if(keywordListID !== undefined && keywordListID !== '-1' && keywordList.length !== 0){
    const kwListItem = []
    for (const keyword of keywordList.keywords) {
      kwListItem.push({ 'keyword': keyword });
    }
    setKeywordListItems(kwListItem);
  }
  },[keywordList.length])

  
  // @ViewChildren('keywordInput') set newInput(inputs: QueryList<ElementRef>) {
  //   if (inputs) {
  //     if (this.newPressed) {
  //       setTimeout(() => {
  //         inputs.last.nativeElement.focus();
  //         this.newPressed = false;
  //       }, 0);
  //     }
  //   }
  // }


  const saveKeywordList = () => {
    if (!isValid()) {
      return;
    }
    const keywords = keywordListItems.filter(item => item.keyword != null).map(item => item.keyword);
    console.log(keywordList.name);
    console.log(keywords);
    if (keywordListID === '-1') {
      new KeywordService().createKeywordList(keywordList.name, keywords).then(
        response => {
          if (response.status === 200) {
            goBackToKeywordLists();
          } else {
            alert(response.json()['message']);
          }
        },
        apierror => {
          console.log("Keyword-items-components func: saveKeywordList 2 ", apierror)
        });
    } else {
      new KeywordService().updateKeywordList(keywordListID, keywordList.name, keywords).then(
        response => {
          if (response.status === 200) {
            goBackToKeywordLists();
          } else {
            alert(response.json()['message']);
          }
        },
        apierror => {
          console.log("Keyword-items-components func: saveKeywordList 3 ", apierror)
        });
    }
  }

  const addNewKeyword = () => {
    const emptyItems = keywordListItems.filter(item => !item.keyword);
    for (const emptyItem of emptyItems) {
      removeKeyword(emptyItem);
    }
    setNewPressed(true);
    keywordListItems.push(new KeywordListItemModel());
    if (newPressed) {
      setTimeout(() => {
        setNewPressed(false);
      }, 0);
    }

  }

  const removeKeyword = (item) => {
    setKeywordListItems(keywordListItems.filter(k => k !== item));
  }

  const checkName = (event) => {
    // TBD: Set name rules.
    keywordList.name = event.target.value
    setValidName(true);
    if (validName) {
      if (event.which === 13) { // Enter
        addNewKeyword();
      }
    }
  }

  const checkKeyword = (keyword, event) => {
    keyword.keyword = event.target.value
    if (!keyword.keyword) {
      return;
    }
    const new_keyword = keyword.keyword.trim().toLowerCase();
    if (new_keyword.length === 0) {
      keyword.error = true
      setKeywordError('Your keyword is empty.');
    } else if (!new_keyword.match('^[A-Za-z0-9\']+$')) {
      keyword.error = true
      setKeywordError('Your keyword contains one or more invalid characters. Please only use alphabets and numbers.'
        + ' Spaces and special characters are not allowed.');
    } else if (keywordListItems.find(k => k.keyword === keyword.keyword && k !== keyword)) {
      keyword.error = true
      setKeywordError('Your list already contains that keyword.');
    } else {
      keyword.error = null
      setKeywordError("");
    }
    if (keyword.error === null && keyworderror === "") {
      if (event.which === 13) { // Enter
        addNewKeyword();
      }
    }
  }

  // const trackByFn = (index, item)=> {
  //   return item.value;
  // }

  const isValid = () => {
    let ret = false;
    if (keywordList && keywordListItems && keywordListItems.length !== 0) {
      ret = (validName && keywordListItems.filter(k => k.error != null).length === 0
        && keywordListItems.filter(k => k.keyword && k.keyword.length !== 0).length > 0);
    }

   
    return ret;
  }

  const goBackToKeywordLists = () => {
    if (location.pathname == '/keyword-lists/new-session') {
      //save keyword list too
      navigate('/sessions/new', {state: location.state});
    } else {
      navigate('/keyword-lists');
    }
  }
  
  return (
    <KeywordListPages
      navigate={goBackToKeywordLists}
      saveKeywordList={saveKeywordList}
      keywordListItems={keywordListItems}
      keywordList={keywordList}
      checkKeyword={checkKeyword}
      removeKeyword={removeKeyword}
      addNewKeyword={addNewKeyword}
      checkName={checkName}
      isValid={isValid()}
      keywordError={keyworderror}
    />
  )
}

export { KeywordListItemsComponent }
