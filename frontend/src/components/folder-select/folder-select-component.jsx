import { useEffect, useState } from "react";
import { useSearchParams } from 'react-router-dom';
import {AppFolderPage} from './html-pages'

function AppFolderSelectComponent(props){
  const [_folders, setFolders] = useState(props.selectableFolders);
  const [visibleFolders, setVisibleFolders] = useState([]);
  const [selectedFolder, setSelectFolder] = useState(null);
  const [breadcrumbs, setBreadCrumbs] = useState([]);
  const [recentFolder, setRecentFolder] = useState(null) ;
  const [searchParam, setSearchParam] = useSearchParams();


  useEffect(()=>{
    if(Object.keys(props.selectableFolders).length !== 0){
      displayFolder()
    } 
  },[])

  useEffect(()=> {
    const folder = searchParam.get('folder');
    const reFolder = _folders.find(f => f.id === (parseInt(folder, 10)))
    setRecentFolder(reFolder);
      if (reFolder) {
        displayFolder(reFolder.parent);
      }
  },[])

  // @Output() itemSelected = new EventEmitter<any>();



  const getbreadcrumb = (folderid)=>{
    const crumbnames = breadcrumbs.map(b => b.name);
    if (folderid !== -1) {
      const currentFolder = _folders.find(f => f.id === folderid);
      crumbnames.push(currentFolder.name);
    }
    crumbnames.unshift('Home');
    return crumbnames.join('/');
  }

  
  const displayFolder = (folderId) =>{
    if (!folderId || folderId === undefined) {
      setVisibleFolders(_folders.filter(f => f.parent == null));
      setBreadCrumbs([]);
    } else {
      setVisibleFolders(_folders.filter(x => x.parent === folderId));
      const bread = [] 
      let folder = _folders.find(f => f.id === folderId);
      bread.unshift(folder);
      if(folder){
      while (folder.parent) {
        folder = _folders.find(f => f.id === folder.parent);
        bread.unshift(folder);
      }
    }
    setBreadCrumbs(bread);
    }
  }

  const hasChildren = (folder)=> {
    const children = _folders.filter(x => x.parent === folder.id);
    return children.length > 0;
  }

  const setSelectedFolderEvent = (id) =>{
    props.setFolderSelect(id)
    if(props.setBreadCrumbSelect){
      const bread = getbreadcrumb(id)
      props.setBreadCrumbSelect(bread)
      //setBreadCrumbs(bread)
    }
    setSelectFolder(id);
  }

  return(
    <AppFolderPage
      visibleFolders = {visibleFolders}
      breadcrumbs = {breadcrumbs}
      displayFolder = {displayFolder}
      setSelectedFolderEvent = {setSelectedFolderEvent}
      selectedFolder = {selectedFolder}
      hasChildren = {hasChildren}
    />
  )
}

export {AppFolderSelectComponent}
