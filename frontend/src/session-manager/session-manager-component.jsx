import { useEffect, useState } from 'react';
import { useParams, Outlet } from 'react-router-dom';
import { ActiveSessionService } from '../services/active-session-service';
import { AppSpinner } from "../spinner/spinner-component"


function SessionManagerComponent() {

  const [activeSessionService, setActiveSessionService] = useState(new ActiveSessionService());
  const [initialized, setInitialized] = useState(false)
  const { sessionId } = useParams();


  useEffect(() => {
    if (sessionId !== undefined) {
      activeSessionService.initialize(sessionId,setInitialized);
    }

    //THROWS ERROR AROUND HERE
    return () => {
      activeSessionService.close();
    }
  }, [])


  if (!initialized) {
    return (
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <AppSpinner/>
      </div>
    );
  }

  return (
    <Outlet context={[activeSessionService, setActiveSessionService]}/>
  );

}

export {SessionManagerComponent}
