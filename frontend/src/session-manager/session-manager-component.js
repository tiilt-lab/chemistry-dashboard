import { useEffect, useState } from 'react';
import { useParams, Outlet } from 'react-router-dom';
import { ActiveSessionService } from '../services/active-session-service';


function SessionManagerComponent() {

  const [activeSessionService, setActiveSessionService] = useState(new ActiveSessionService());
  const { sessionId } = useParams();

  useEffect(() => {
    if (sessionId !== undefined) {
      activeSessionService.initialize(sessionId);
    }

    return () => {
      activeSessionService.close();
    }
  }, [])

  if (!activeSessionService.initialized) {
    return <></>
  }

  return (
    <Outlet context={[activeSessionService, setActiveSessionService]}/>
  )

}

export {SessionManagerComponent}