import { KeywordService } from "../services/keyword-service";
import { KeywordListModel } from '../models/keyword-list';
import { formatDate } from "../globals";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { KeywordListPage } from './html-pages'


function ManageKeywordListsComponent() {
  const navigate = useNavigate();
  const [deleteDialogIsOpen, setDeleteDialogIsOpen] = useState(false);
  const [keywordListToDelete, setKeywordListToDelete] = useState(null);
  const [keywordLists, setKeywordLists] = useState([]);
  const [topics, setTopics] = useState([]);

  const formatdate = formatDate; // Allows the HTML to invoke the function.

  useEffect(() => {
    const fetchData = new KeywordService().getKeywordLists();
    fetchData.then(
      (response) => {
        if (response.status === 200) {
          const resp = response.json()
          resp.then(
            (result) => {
              let keywordss = '';
              const kwordLists = KeywordListModel.fromJsonList(result)
              setKeywordLists(kwordLists)
              
            },
            (err) => { console.log('ManageKeywordListsComponent error func : useeffect 122' ,err) })

        } else {
          console.log('ManageKeywordListsComponent error func : useeffect 1', response)
        }
      },
      (apierror) => {
        console.log('ManageKeywordListsComponent error func : useeffect 2', apierror)
      }
    )
  }, []);


  const openNewKeywordList = () => {
    return navigate('/keyword-lists/new-keyword-list');
  }

  const createTopicModel = () => {
    const fetchData = new KeywordService().getTopics();
    fetchData.then(
      (response) => {
        if (response.status === 200) {
          setTopics(response.json())
          for (const topic of topics) {
            console.log("Topic: ", topic);
          }
        } else {
          console.log('ManageKeywordListsComponent error func : createTopicModel 1', response)
        }
      },
      (apierror) => {
        console.log('ManageKeywordListsComponent error func : createTopicModel 2', apierror)
      }
    )
  }

  const keywordListClicked = (keywordList) => {
    return navigate("/keyword-lists/" + keywordList.id);
  }

  const navigateToHomeScreen = () => {
    return navigate("/home");
  }

  const closeDeleteDialog = () => {
    setDeleteDialogIsOpen(false);
  }

  // Open confirmation dialog.
  const deleteKeywordList = (keywordList) => {
    setKeywordListToDelete(keywordList);
    setDeleteDialogIsOpen(true);
  }

  // Deletes a keyword list.  Called from confirmation dialog.
  const confirmDeleteKeywordList = () => {
    const fetchData = new KeywordService().deleteKeywordList(keywordListToDelete.id)
    fetchData.then(
      (result) => {
        const filtered = keywordLists.filter(
          (kl) => kl.id !== keywordListToDelete.id
        );
        setKeywordLists(filtered)
        setKeywordListToDelete(null);
        closeDeleteDialog();
      },
      (apierror) => {
        console.log("ManageKeywordListsComponent error func: confirmDeleteKeywordList, Failed to delete keyword list.", apierror);
        closeDeleteDialog();
      }
    );
  }

  // const formatKeywords = (keywords)=> {
  //   if (keywords) {
  //     return keywords.map((k) => k.keyword).join(", ");
  //   }
  //   return "";
  // }

  return (
    <KeywordListPage
      formatdate={formatdate}
      deleteDialogIsOpen={deleteDialogIsOpen}
      closeDeleteDialog={closeDeleteDialog}
      keywordLists={keywordLists}
      navigate={navigateToHomeScreen}
      keywordListClicked={keywordListClicked}
      deleteKeywordList={deleteKeywordList}
      openNewKeywordList={openNewKeywordList}
      createTopicModel={createTopicModel}
      confirmDeleteKeywordList={confirmDeleteKeywordList}
    />
  )
}

export { ManageKeywordListsComponent }