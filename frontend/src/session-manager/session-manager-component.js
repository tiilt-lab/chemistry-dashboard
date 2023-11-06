import { useEffect, useState } from 'react';
import { useParams, Outlet } from 'react-router-dom';
import { ActiveSessionService } from '../services/active-session-service';


function SessionManagerComponent() {

  const [activeSessionService, setActiveSessionService] = useState(new ActiveSessionService());
  const [initialized, setInitialized] = useState(false)
  const { sessionId } = useParams();
  

  useEffect(() => {
    if (sessionId !== undefined) {
      activeSessionService.initialize(sessionId,setInitialized);
    }
    
    console.log("HERE 4");
    //THROWS ERROR AROUND HERE

    return () => {
      console.log("HERE 5");
      activeSessionService.close();
      console.log("HERE 6");
    }
  }, [])


  if (!initialized) {
    return <></>
  }

  return (
    
    <Outlet context={[activeSessionService, setActiveSessionService]}/>
  )

}

export {SessionManagerComponent}
