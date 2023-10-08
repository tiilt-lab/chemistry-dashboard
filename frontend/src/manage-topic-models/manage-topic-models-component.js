import { KeywordService } from "../services/keyword-service";
import { TopicModelService } from "../services/topic-model-service";
import { TopicModelModel } from '../models/topic-model';
import { formatDate } from "../globals";
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ManageTopicsPage } from './html-pages'


function ManageTopicModelsComponent(props) {
  const navigate = useNavigate();
  const [deleteDialogIsOpen, setDeleteDialogIsOpen] = useState(false);
  const [topicModelToDelete, setTopicModelToDelete] = useState(null);
  const [topicModels, setTopicModels] = useState([]);
  const [topics, setTopics] = useState([]);
  //const location = useLocation();

  const formatdate = formatDate; // Allows the HTML to invoke the function.

  useEffect(() => {
    const fetchData = new TopicModelService().getTopicModels();
    fetchData.then(
      (response) => {
        if (response.status === 200) {
          const resp = response.json()
          resp.then(
            (result) => {
              const topModels = TopicModelModel.fromJsonList(result)
              for (let i = 0; i < topModels.length; i++) {
                let split = topModels[i].summary.split("\n");
                if (split.length > 1) {
                  topModels[i].summary = split[0];
                  //but it's not just this. you have to go and select the topics that were selected
                  //then interaction where you can print the data if it exists for each topic
                  topModels[i].data = split[1];
                }
              }
              setTopicModels(topModels)
            },
            (err) => { console.log('ManageTopicModelsComponent error func : useeffect 122' ,err) })

        } else {
          console.log('ManageTopicModelsComponent error func : useeffect 1', response)
        }
      },
      (apierror) => {
        console.log('ManageTopicModelsComponent error func : useeffect 2', apierror)
      }
    )
  }, []);

  //console.log(location.state, 'debugging ..')

  const navFileUpload = () => {
    navigate("/file_upload");
  }
  
  const navTopicList = (dataToPrint, topicNames, title) => {
    if (typeof dataToPrint !== "undefined") {
       navigate('/topic-list', {state: {topics:dataToPrint, names:topicNames.replace(/ /g, ''), title:title}});
    } else {
      console.log("Can't load model");
    }
  }

  const createTopicModel = () => {
    const fetchData = new TopicModelService().getTopics();
    fetchData.then(
      (response) => {
        if (response.status === 200) {
          setTopics(response.json())
          for (const topic of topics) {
            console.log("Topic: ", topic);
          }
        } else {
          console.log('ManageTopicModelComponent error func : createTopicModel 1', response)
        }
      },
      (apierror) => {
        console.log('ManageTopicModelComponent error func : createTopicModel 2', apierror)
      }
    )
  }

  const navigateToHomeScreen = () => {
    return navigate("/home");
  }

  const closeDeleteDialog = () => {
    setDeleteDialogIsOpen(false);
  }

  // Open confirmation dialog.
  const deleteTopicModel = (topicmodel) => {
    setTopicModelToDelete(topicmodel);
    setDeleteDialogIsOpen(true);
  }

  // Deletes a keyword list.  Called from confirmation dialog.
  const confirmDeleteTopicModel = () => {
    const fetchData = new TopicModelService().deleteTopicModel(topicModelToDelete.id)
    fetchData.then(
      (result) => {
        const filtered = topicModels.filter(
          (kl) => kl.id !== topicModelToDelete.id
        );
        setTopicModels(filtered)
        setTopicModelToDelete(null);
        closeDeleteDialog();
      },
      (apierror) => {
        console.log("ManageTopicModelsComponent error func: confirmDeleteTopicModels, Failed to delete topic model.", apierror);
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
    <ManageTopicsPage
      formatdate={formatdate}
      deleteDialogIsOpen={deleteDialogIsOpen}
      closeDeleteDialog={closeDeleteDialog}
      topicModels={topicModels}
      navigate={navigateToHomeScreen}
      deleteTopicModel={deleteTopicModel}
      createTopicModel={createTopicModel}
      confirmDeleteTopicModel={confirmDeleteTopicModel}
      navFileUpload = {navFileUpload}
      navTopicList = {navTopicList}
    />
  )
}

export { ManageTopicModelsComponent }
