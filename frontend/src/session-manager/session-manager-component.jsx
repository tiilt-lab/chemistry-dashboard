import { useEffect, useState, useMemo } from 'react';
import { useParams, Outlet } from 'react-router-dom';
import { getActiveSessionService } from '../services/active-session-singleton';
import { AppSpinner } from "../spinner/spinner-component"


function SessionManagerComponent() {

  // Get the singleton service instance
  const activeSessionService = getActiveSessionService();

  const [initialized, setInitialized] = useState(false)
  const { sessionId } = useParams();

  useEffect(() => {
    if (sessionId !== undefined) {
      console.log('SessionManagerComponent: Setting up for sessionId:', sessionId);

      // Check if service is already initialized with data
      if (activeSessionService.sessionId === sessionId &&
          activeSessionService.initialized &&
          activeSessionService.getSession() !== null) {
        console.log('SessionManagerComponent: Service already initialized with data');
        setInitialized(true);
      } else {
        // Initialize the service for this session
        activeSessionService.initialize(sessionId, (ready) => {
          console.log('SessionManagerComponent: Service initialized via callback:', ready);
          setInitialized(ready);
        });
      }
    }

    // Cleanup: ONLY when the entire component unmounts (leaving the session entirely)
    return () => {
      // We're unmounting the SessionManagerComponent entirely
      // This happens when navigating away from /sessions/:id/* routes
      console.log('SessionManagerComponent: Component unmounting');
      // Don't close here - let the service persist
    }
  }, [sessionId]) // Only re-run when sessionId changes


  // Stabilize the context value to prevent unnecessary re-renders
  const contextValue = useMemo(() => [activeSessionService, () => {}], [activeSessionService]);

  if (!initialized) {
    return (
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <AppSpinner/>
      </div>
    );
  }

  return (
    <Outlet context={contextValue}/>
  );

}

export {SessionManagerComponent}
